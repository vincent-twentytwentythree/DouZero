import os 
import typing
import logging
import traceback
import numpy as np
from collections import Counter
import time

import torch 
from torch import multiprocessing as mp

from .env_utils import Environment, getDevice
from douzero.env import Env
from douzero.env.env import _cards2array, _get_one_hot_array

shandle = logging.StreamHandler()
shandle.setFormatter(
    logging.Formatter(
        '[%(levelname)s:%(process)d %(module)s:%(lineno)d %(asctime)s] '
        '%(message)s'))
log = logging.getLogger('doudzero')
log.propagate = False
log.addHandler(shandle)
log.setLevel(logging.INFO)

# Buffers are used to transfer data between actor processes
# and learner processes. They are shared tensors in GPU
Buffers = typing.Dict[str, typing.List[torch.Tensor]]

# Environment -> Env -> GameEnv
def create_env(flags):
    return Env(flags.objective, flags)

def get_batch(free_queue,
              full_queue,
              buffers,
              flags,
              lock):
    """
    This function will sample a batch from the buffers based
    on the indices received from the full queue. It will also
    free the indices by sending it to full_queue.
    """
    with lock:
        indices = [full_queue.get() for _ in range(flags.batch_size)]
    batch = {
        key: torch.stack([buffers[key][m] for m in indices], dim=1)
        for key in buffers
    }
    for m in indices:
        free_queue.put(m)
    return batch

def create_optimizers(flags, learner_model):
    """
    Create three optimizers for the three positions
    """
    positions = [flags.training_mode]
    optimizers = {}
    for position in positions:
        optimizer = torch.optim.RMSprop(
            learner_model.parameters(position),
            lr=flags.learning_rate,
            momentum=flags.momentum,
            eps=flags.epsilon,
            alpha=flags.alpha)
        optimizers[position] = optimizer
    optimizers['pk_dp'] = optimizers[flags.training_mode]
    return optimizers

def create_buffers(flags, device_iterator):
    """
    We create buffers for different positions as well as
    for different devices (i.e., GPU). That is, each device
    will have three buffers for the three positions.
    """
    T = flags.unroll_length
    positions = ['landlord', 'second_hand', 'pk_dp']
    buffers = {}
    for device in device_iterator:
        buffers[device] = {}
        for position in positions:
            x_dim = 17 # MYWEN
            specs = dict(
                done=dict(size=(T,), dtype=torch.bool),
                episode_return=dict(size=(T,), dtype=torch.float32),
                target_adp=dict(size=(T,), dtype=torch.float32),
                target_wp=dict(size=(T,), dtype=torch.float32),
                obs_x_no_action=dict(size=(T, x_dim), dtype=torch.int8),
                obs_action=dict(size=(T, 42), dtype=torch.int8), # MYWEN
                obs_z=dict(size=(T, 20, 42), dtype=torch.int8), # MYWEN
            )
            _buffers: Buffers = {key: [] for key in specs}
            for _ in range(flags.num_buffers):
                for key in _buffers:
                    if device == 'mps':
                        _buffer = torch.empty(**specs[key]).to(getDevice(deviceName=device))
                    else :
                        _buffer = torch.empty(**specs[key]).to(getDevice(deviceName=device)).share_memory_()
                    _buffers[key].append(_buffer)
            buffers[device][position] = _buffers
    return buffers


# buffer
# {
#     device: {
#         position: {
#             "key": [ size of buffers
#                 {
#                     "1": value
#                     "T": value
#                 }
#             ]
#         }
#     }
# }

# free_queue
# {
#     device: {
#         position: queue size of num_buffers
#     }
# }
def act(i, device, free_queue, full_queue, model, buffers, flags): # MYWEN
    """
    This function will run forever until we stop it. It will generate
    data from the environment and send the data to buffer. It uses
    a free queue and full queue to syncup with the main process.
    """
    positions = [flags.training_mode, 'pk_dp']
    try:
        T = flags.unroll_length
        log.info('Device %s Actor %i started.', str(device), i)

        env = create_env(flags)
        env = Environment(env, device)

        # done_buf: label actions whether game is down for each position
        # episode_return_buf: reward only when game down for each position
        # target_buf: reward for each action for each position
        # obs_x_no_action_buf = {p: [] for p in positions}
        # obs_action_buf: action list for each position
        # obs_z_buf = {p: [] for p in positions}
        # size: total action number for each position
        done_buf = {p: [] for p in positions}
        episode_return_buf = {p: [] for p in positions}
        target_adp_buf = {p: [] for p in positions}
        target_wp_buf = {p: [] for p in positions}
        obs_x_no_action_buf = {p: [] for p in positions}
        obs_action_buf = {p: [] for p in positions}
        obs_z_buf = {p: [] for p in positions}
        size = {p: 0 for p in positions}

        position, obs, env_output = env.initial()
        deckCardBatch = []
        while True:
            while True:
                obs_x_no_action_buf[position].append(env_output['obs_x_no_action'])
                if position == "pk_dp":
                    _action_idx = env.getMockActionIndex(True)
                # elif position == "landlord":
                else:
                    with torch.no_grad():
                        agent_output = model.forward(position, obs['z_batch'], obs['x_batch'], flags=flags)
                    _action_idx = int(agent_output['action'].cpu().detach().numpy())
                # else:
                #     with torch.no_grad():
                #         agent_output = model.forward(position, obs['z_batch'], obs['x_batch'], flags=flags)
                #     _action_idx = int(agent_output['action'].cpu().detach().numpy())
                #     _random = bool(agent_output['random'].cpu().detach().numpy())
                #     if _random == False:
                #         _action_idx_pk = env.getMockActionIndex(False)
                #         score = env.calculateScore(obs['legal_actions'][_action_idx])
                #         score_pk = env.calculateScore(obs['legal_actions'][_action_idx_pk])
                #         if score < score_pk:
                #             _action_idx = _action_idx_pk
                action = obs['legal_actions'][_action_idx]
                other_details = obs['other_details'][_action_idx]
                obs_z_buf[position].append(torch.vstack((_cards2tensor(other_details, action), env_output['obs_z'])))
                obs_action_buf[position].append(torch.from_numpy(_cards2array(action)))
                size[position] += 1
                position, obs, env_output = env.step(action)
                if env_output['done']:
                    # if env_output['episode_return'] <= -20:
                    #     deckCardBatch.append(env.getDeckCards())
                    #     if len(deckCardBatch) > 20:
                    #         with lock:
                    #             with open("outputDeckCards.txt", "a") as file:
                    #                 for deckCard in deckCardBatch:
                    #                     file.write(", ".join(map(str, deckCard)) + "\n")
                    #             deckCardBatch = []
                    for p in positions:
                        diff = size[p] - len(target_adp_buf[p])
                        if diff > 0:
                            done_buf[p].extend([False for _ in range(diff-1)])
                            done_buf[p].append(True)
                            episode_return = env_output['episode_return'] if p == flags.training_mode else -env_output['episode_return'] # MYWEN / 24
                            wp_return = 1. if episode_return > 0. else -1.
                            episode_return_buf[p].extend([0.0 for _ in range(diff-1)])
                            episode_return_buf[p].append(episode_return)
                            target_adp_buf[p].extend([episode_return for _ in range(diff)])
                            target_wp_buf[p].extend([wp_return for _ in range(diff)])
                    break
            for p in positions:
                while size[p] > T: 
                    index = free_queue[p].get()
                    if index is None:
                        break
                    for t in range(T):
                        buffers[p]['done'][index][t, ...] = done_buf[p][t]
                        buffers[p]['episode_return'][index][t, ...] = episode_return_buf[p][t]
                        buffers[p]['target_adp'][index][t, ...] = target_adp_buf[p][t]
                        buffers[p]['target_wp'][index][t, ...] = target_wp_buf[p][t]
                        buffers[p]['obs_x_no_action'][index][t, ...] = obs_x_no_action_buf[p][t]
                        buffers[p]['obs_action'][index][t, ...] = obs_action_buf[p][t]
                        buffers[p]['obs_z'][index][t, ...] = obs_z_buf[p][t]
                    full_queue[p].put(index)
                    done_buf[p] = done_buf[p][T:]
                    episode_return_buf[p] = episode_return_buf[p][T:]
                    target_adp_buf[p] = target_adp_buf[p][T:]
                    target_wp_buf[p] = target_wp_buf[p][T:]
                    obs_x_no_action_buf[p] = obs_x_no_action_buf[p][T:]
                    obs_action_buf[p] = obs_action_buf[p][T:]
                    obs_z_buf[p] = obs_z_buf[p][T:]
                    size[p] -= T

    except KeyboardInterrupt:
        pass  
    except Exception as e:
        log.error('Exception in worker process %i', i)
        traceback.print_exc()
        print()
        raise e

def _cards2tensor(other_details, list_cards):
    """
    Convert a list of integers to the tensor
    representation
    See Figure 2 in https://arxiv.org/pdf/2106.06135.pdf
    """
    attributes1 = np.hstack(( # mywen
        _get_one_hot_array(other_details[0], 7),
        _get_one_hot_array(other_details[1], 7),
        _get_one_hot_array(other_details[2], 7),
        _get_one_hot_array(other_details[3], 7),
        _get_one_hot_array(other_details[4], 7),
        _get_one_hot_array(other_details[5], 7),
    ))
    attributes2 = np.hstack(( # mywen
        _get_one_hot_array(other_details[6], 10),
        _get_one_hot_array(other_details[6], 10),
        _get_one_hot_array(other_details[7], 7),
        _get_one_hot_array(other_details[8], 10),
        [0] * 5,
    ))
    matrix = np.vstack((_cards2array(list_cards), # 1 * 42
                        [attributes1], # 1 * 42
                        [attributes2], # 1 * 42
    )) # 20 * 42
    matrix = torch.from_numpy(matrix)
    return matrix