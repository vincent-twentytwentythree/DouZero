"""
Here, we wrap the original environment to make it easier
to use. When a game is finished, instead of mannualy reseting
the environment, we do it automatically.
"""
import numpy as np
import torch 

def getDevice(deviceName):
    if deviceName == "mps":
        device = torch.device('mps')
    elif deviceName == "cpu":
        device = torch.device('cpu')
    else :
        device = torch.device('cuda:'+str(deviceName))
    return device

# @positon: landlord second_hand pk_dp
# @obs: from infoset
# @x_no_action: all cards and actions info, no batch
# @z: card_play_action_seq
def _format_observation(obs, device):
    """
    A utility function to process observations and
    move them to CUDA.
    """
    position = obs['position']
    device = getDevice(device)
    x_batch = torch.from_numpy(obs['x_batch']).to(device)
    z_batch = torch.from_numpy(obs['z_batch']).to(device)
    x_no_action = torch.from_numpy(obs['x_no_action'])
    z = torch.from_numpy(obs['z'])
    obs = {'x_batch': x_batch,
           'z_batch': z_batch,
           'legal_actions': obs['legal_actions'],
           'other_details': obs['other_details']
           }
    return position, obs, x_no_action, z

class Environment:
    def __init__(self, env, device):
        """ Initialzie this environment wrapper
        """
        self.env = env
        self.device = device
        self.episode_return = None
        self.deck_cards = []

    # @positon: landlord second_hand pk_dp
    # @obs: from infoset
    # @@initial_done: whether game is down
    # @@episode_return: reward
    # @@x_no_action: all cards and actions info, no batch
    # @@z: card_play_action_seq
    def initial(self):
        initial_position, initial_obs, x_no_action, z = _format_observation(self.env.reset(), self.device)
        initial_reward = torch.zeros(1, 1)
        self.episode_return = torch.zeros(1, 1)
        initial_done = torch.ones(1, 1, dtype=torch.bool)

        return initial_position, initial_obs, dict(
            done=initial_done,
            episode_return=self.episode_return,
            obs_x_no_action=x_no_action,
            obs_z=z,
            )
        
    # MYWEN
    def step(self, action):
        obs, reward, done, _ = self.env.step(action)

        self.episode_return += reward
        episode_return = self.episode_return

        if done:
            self.deck_cards = self.env.getDeckCards()
            obs = self.env.reset()
            self.episode_return = torch.zeros(1, 1)

        position, obs, x_no_action, z = _format_observation(obs, self.device)
        reward = torch.tensor(reward).view(1, 1)
        done = torch.tensor(done).view(1, 1)
        
        return position, obs, dict(
            done=done,
            episode_return=episode_return,
            obs_x_no_action=x_no_action,
            obs_z=z,
            )

    def close(self):
        self.env.close()

    def getDeckCards(self):
        return self.deck_cards
