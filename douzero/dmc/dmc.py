import os
import threading
import time
import timeit
import pprint
from collections import deque
import numpy as np

import torch
from torch import multiprocessing as mp
from torch import nn

from .file_writer import FileWriter
from .models import Model
from .utils import get_batch, log, create_env, create_buffers, create_optimizers, act, getDevice


# mp.set_start_method("spawn", force=True)

mean_episode_return_buf = {p:deque(maxlen=100) for p in ['landlord', 'second_hand', 'pk_dp']}

def compute_loss(logits, targets):
    loss = ((logits.squeeze(-1) - targets) ** 2).mean()
    return loss

def compute_loss_(logits, targets):
    loss = ((logits.squeeze(-1) - targets) ** 2)
    return loss

def learn(position,
          actor_models,
          model,
          batch,
          optimizer,
          flags,
          lock):
    """Performs a learning (optimization) step."""
    device = getDevice(deviceName=flags.training_device)
    obs_x = batch["obs_x_no_action"]
    obs_x = torch.flatten(obs_x, 0, 1).to(device)
    obs_z = torch.flatten(batch['obs_z'].to(device), 0, 1).float()
    target_adp = torch.flatten(batch['target_adp'].to(device), 0, 1)
    target_wp = torch.flatten(batch['target_wp'].to(device), 0, 1)
    episode_returns = batch['episode_return'][batch['done']]
    mean_episode_return_buf[position].append(torch.mean(episode_returns).to(device))
        
    with lock:
        win_rate, win, lose = model.forward(obs_z, obs_x, return_value=True)['values']

        loss1 = compute_loss(win_rate, target_wp)
        l_w = compute_loss_(win, target_adp) * (1. + target_wp) / 2.
        l_l = compute_loss_(lose, target_adp) * (1. - target_wp) / 2.
        loss2 = l_w.mean() + l_l.mean()
        loss = loss1 + loss2

        stats = {
            'mean_episode_return_'+position: torch.mean(torch.stack([_r for _r in mean_episode_return_buf[position]])).item(),
            'loss_'+position: loss.item(),
            'loss1_'+position: loss1.item(),
            'loss2_'+position: loss2.item(),
        }
        
        optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), flags.max_grad_norm)
        optimizer.step()

        for actor_model in actor_models.values():
            actor_model.get_model(position).load_state_dict(model.state_dict())
        return stats

def train(flags):
    """
    This is the main funtion for training. It will first
    initilize everything, such as buffers, optimizers, etc.
    Then it will start subprocesses as actors. Then, it will call
    learning function with  multiple threads.
    """
    training_mode = flags.training_mode
    print ("MYWEN", training_mode)
    if not flags.actor_device_cpu or flags.training_device != 'cpu':
        if not torch.cuda.is_available() and not torch.mps.is_available():
            raise AssertionError("CUDA not available. If you have GPUs, please specify the ID after `--gpu_devices`. Otherwise, please train with CPU with `python3 train.py --actor_device_cpu --training_device cpu`")
    plogger = FileWriter(
        xpid=flags.xpid,
        xp_args=flags.__dict__,
        rootdir=flags.savedir,
    )
    checkpointpath = os.path.expandvars(
        os.path.expanduser('%s/%s/%s' % (flags.savedir, flags.xpid, training_mode + '_model.tar'))) # todo

    T = flags.unroll_length
    B = flags.batch_size

    if flags.actor_device_cpu:
        device_iterator = ['cpu']
    elif flags.actor_device_mps:
        device_iterator = ['mps']
    else:
        assert abs(flags.num_actor_devices) <= len(flags.gpu_devices.split(',')), 'The number of actor devices can not exceed the number of available devices'
        if flags.num_actor_devices > 0:
            device_iterator = flags.gpu_devices.split(',')[:flags.num_actor_devices]
        else:
            device_iterator = flags.gpu_devices.split(',')[flags.num_actor_devices:]

    # Initialize actor models
    models = {}
    for device in device_iterator:
        model = Model(device=device, training_mode=training_mode)
        model.share_memory()
        model.eval()
        models[device] = model

    # Initialize buffers
    buffers = create_buffers(flags, device_iterator)
   
    # Initialize queues
    actor_processes = []
    ctx = mp.get_context('spawn')
    free_queue = {}
    full_queue = {}
        
    for device in device_iterator:
        _free_queue = {'landlord': ctx.SimpleQueue(), 'second_hand': ctx.SimpleQueue(), 'pk_dp': ctx.SimpleQueue()}
        _full_queue = {'landlord': ctx.SimpleQueue(), 'second_hand': ctx.SimpleQueue(), 'pk_dp': ctx.SimpleQueue()}
        free_queue[device] = _free_queue
        full_queue[device] = _full_queue

    # Learner model for training
    learner_model = Model(device=flags.training_device, training_mode=training_mode)

    # Create optimizers
    optimizers = create_optimizers(flags, learner_model)

    # Stat Keys
    stat_keys = [
        'mean_episode_return_landlord',
        'loss_landlord',
        'loss1_landlord',
        'loss2_landlord',
        'mean_episode_return_second_hand',
        'loss_second_hand',
        'loss1_second_hand',
        'loss2_second_hand',
        'mean_episode_return_pk_dp',
        'loss_pk_dp',
    ]
    frames, stats = 0, {k: 0 for k in stat_keys}
    position_frames = {'landlord':0, 'second_hand':0, 'pk_dp':0}

    # Load models if any
    if flags.load_model and os.path.exists(checkpointpath):
        device = getDevice(deviceName=flags.training_device)
        checkpoint_states = torch.load(
            checkpointpath, map_location=(device)
        )
        for k in ['pk_dp']:
            learner_model.get_model(k).load_state_dict(checkpoint_states["model_state_dict"][k])
            optimizers[k].load_state_dict(checkpoint_states["optimizer_state_dict"][k])
            for device in device_iterator:
                models[device].get_model(k).load_state_dict(learner_model.get_model(k).state_dict())
        for k in checkpoint_states["stats"]:
            stats[k] = checkpoint_states["stats"][k]
        frames = checkpoint_states["frames"]
        position_frames = checkpoint_states["position_frames"]
        log.info(f"Resuming preempted job, current stats:\n{stats}")

    # Starting actor processes
    for device in device_iterator:
        num_actors = flags.num_actors
        for i in range(flags.num_actors):
            actor = ctx.Process(
                target=act,
                args=(i, device, free_queue[device], full_queue[device], models[device], buffers[device], flags))
            actor.start()
            actor_processes.append(actor)

    def batch_and_learn(i, device, position, get_data_device_locks, learn_model_position_lock, lock=threading.Lock()):
        """Thread target for the learning process."""
        nonlocal frames, position_frames, stats
        while frames < flags.total_frames:
            log.info("batch_and_learn start %d %s %s", i, str(device), position)
            batch = get_batch(free_queue[device][position], full_queue[device][position], buffers[device][position], flags, get_data_device_locks)
            _stats = learn(position, models, learner_model.get_model(position), batch, 
                optimizers[position], flags, learn_model_position_lock)
            with lock:
                for k in _stats:
                    stats[k] = _stats[k]
                log.info("batch_and_learn finished %d %s %s", i, str(device), position)
                to_log = dict(frames=frames)
                to_log.update({k: stats[k] for k in stat_keys})
                plogger.log(to_log)
                frames += T * B
                position_frames[position] += T * B

    for device in device_iterator:
        for m in range(flags.num_buffers):
            free_queue[device]['landlord'].put(m)
            free_queue[device]['second_hand'].put(m)
            free_queue[device]['pk_dp'].put(m)

    threads = []
    get_data_device_locks = {}
    for device in device_iterator:
        get_data_device_locks[device] = {'landlord': threading.Lock(), 'second_hand': threading.Lock(), 'pk_dp': threading.Lock()}
    # learn_model_position_locks = {'landlord': threading.Lock(), 'second_hand': threading.Lock(), 'pk_dp': threading.Lock()}
    learn_model_position_locks = threading.Lock()

    for device in device_iterator:
        for i in range(flags.num_threads):
            for position in [training_mode, 'pk_dp']:
                thread = threading.Thread(
                    target=batch_and_learn, name='batch-and-learn-%d' % i, args=(i,device,position,get_data_device_locks[device][position],learn_model_position_locks))
                thread.start()
                threads.append(thread)
    
    def checkpoint(frames):
        if flags.disable_checkpoint:
            return
        log.info('Saving checkpoint to %s', checkpointpath)
        _models = learner_model.get_models()
        torch.save({
            'model_state_dict': {k: _models[k].state_dict() for k in _models},
            'optimizer_state_dict': {k: optimizers[k].state_dict() for k in optimizers},
            "stats": stats,
            'flags': vars(flags),
            'frames': frames,
            'position_frames': position_frames
        }, checkpointpath)

        # Save the weights for evaluation purpose
        # for position in [training_mode, 'pk_dp']:
        #     model_weights_dir = os.path.expandvars(os.path.expanduser(
        #         '%s/%s/%s' % (flags.savedir, flags.xpid, position+'_weights_'+training_mode+str(frames)+'.ckpt')))
        #     torch.save(learner_model.get_model(position).state_dict(), model_weights_dir)

    fps_log = []
    timer = timeit.default_timer
    try:
        last_checkpoint_time = timer()
        while frames < flags.total_frames:
            start_frames = frames
            position_start_frames = {k: position_frames[k] for k in position_frames}
            start_time = timer()
            time.sleep(5)

            if timer() - last_checkpoint_time > flags.save_interval * 60:  
                checkpoint(frames)
                last_checkpoint_time = timer()
            end_time = timer()

            fps = (frames - start_frames) / (end_time - start_time)
            fps_log.append(fps)
            if len(fps_log) > 24:
                fps_log = fps_log[1:]
            fps_avg = np.mean(fps_log)

            position_fps = {k:(position_frames[k]-position_start_frames[k])/(end_time-start_time) for k in position_frames}
            log.info('After %i (L:%i U:%i D:%i) frames: @ %.1f fps (avg@ %.1f fps) (L:%.1f U:%.1f D:%.1f) Stats:\n%s',
                     frames,
                     position_frames['landlord'],
                     position_frames['second_hand'],
                     position_frames['pk_dp'],
                     fps,
                     fps_avg,
                     position_fps['landlord'],
                     position_fps['second_hand'],
                     position_fps['pk_dp'],
                     pprint.pformat(stats))
            
            # for device in device_iterator:
            #     log.info("freequeue %d %d %d", len(free_queue[device]['landlord']),
            #         len(free_queue[device]['second_hand']),
            #         len(free_queue[device]['pk_dp'].put(m))
            #     )
            #     log.info("fullqueue %d %d %d", len(full_queue[device]['landlord']),
            #         len(full_queue[device]['second_hand']),
            #         len(full_queue[device]['pk_dp'].put(m))
            #     )

    except KeyboardInterrupt:
        return 
    else:
        for thread in threads:
            thread.join()
        log.info('Learning finished after %d frames.', frames)

    checkpoint(frames)
    plogger.close()
