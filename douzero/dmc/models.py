"""
This file includes the torch models. We wrap the three
models into one class for convenience.
"""

import numpy as np

import torch
from torch import nn
import torch.nn.functional as F

from .env_utils import getDevice

def mish(input):
    return input * torch.tanh(torch.nn.functional.softplus(input))

class ChannelAttention(nn.Module):
    def __init__(self, channel, reduction=4):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Sequential(
            nn.Linear(channel, channel // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channel // reduction, channel, bias=False),
            nn.Sigmoid()
        )

    def forward(self, x):
        b, c, _ = x.size()
        y = self.avg_pool(x).view(b, c)
        y = self.fc(y).view(b, c, 1)
        return x * y.expand_as(x)

class BasicBlockM(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1):
        super(BasicBlockM, self).__init__()
        self.conv1 = nn.Conv1d(in_planes, planes, kernel_size=3,
                               stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm1d(planes)
        # self.mish = nn.Mish(inplace=True)
        self.mish = mish
        self.conv2 = nn.Conv1d(planes, planes, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm1d(planes)
        self.se = ChannelAttention(planes)
        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_planes, self.expansion * planes,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm1d(self.expansion * planes)
            )

    def forward(self, x):
        out = self.mish(self.bn1(self.conv1(x)))
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.se(out)
        out += self.shortcut(x)
        out = self.mish(out)
        return out

class GeneralModelResnet(nn.Module):
    def __init__(self):
        super().__init__()
        self.in_planes = 20
        self.layer1 = self._make_layer(BasicBlockM, 72, 3, stride=2)  # 1*27*72
        self.layer2 = self._make_layer(BasicBlockM, 144, 3, stride=2)  # 1*14*146
        self.layer3 = self._make_layer(BasicBlockM, 288, 3, stride=2)  # 1*7*292
        self.linear1 = nn.Linear(288 * BasicBlockM.expansion * 6 + 17 * 4, 2048)
        self.linear2 = nn.Linear(2048, 512)
        self.linear3 = nn.Linear(512, 128)
        self.linear4 = nn.Linear(128, 3)

    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, z, x, return_value=False, flags=None):

        out = self.layer1(z)
        out = self.layer2(out)
        out = self.layer3(out)
        out = out.flatten(1, 2)
        out = torch.cat([x, x, x, x, out], dim=-1)
        out = F.leaky_relu_(self.linear1(out))
        out = F.leaky_relu_(self.linear2(out))
        out = F.leaky_relu_(self.linear3(out))
        out = self.linear4(out)
        win_rate, win, lose = torch.split(out, (1, 1, 1), dim=-1)
        win_rate = torch.tanh(win_rate)
        _win_rate = (win_rate + 1) / 2
        out = _win_rate * win + (1. - _win_rate) * lose

        if return_value:
            return dict(values=(win_rate, win, lose))
        else:
            if flags is not None and flags.exp_epsilon > 0 and np.random.rand() < flags.exp_epsilon:
                action = torch.randint(out.shape[0], (1,))[0]
            else:
                action = torch.argmax(out, dim=0)[0]
            return dict(action=action, max_value=torch.max(out), values=out)

# Model dict is only used in evaluation but not training
model_dict = {}
model_dict['landlord'] = GeneralModelResnet
model_dict['second_hand'] = GeneralModelResnet
model_dict['pk_dp'] = GeneralModelResnet

class Model:
    """
    The wrapper for the three models. We also wrap several
    interfaces such as share_memory, eval, etc.
    """
    def __init__(self, device=0, training_mode=None):
        self.models = {}
        self.deviceName = device
        self.training_mode = training_mode
        device = getDevice(deviceName=device)
        if training_mode == None:
            self.models['landlord'] = GeneralModelResnet().to(device)
            self.models['second_hand'] = GeneralModelResnet().to(device)
        if training_mode != None:
            self.models[training_mode] = GeneralModelResnet().to(device)
            self.models['pk_dp'] = self.models[training_mode] # todo

    def forward(self, position, z, x, training=False, flags=None, topk=None): # MYWEN
        model = self.models[position]
        return model.forward(z, x, training, flags)

    def share_memory(self):
        if self.deviceName == 'mps':
            return;
        if self.training_mode == None:
            self.models['landlord'].share_memory()
            self.models['second_hand'].share_memory()
        else:
            self.models[self.training_mode].share_memory()

    def eval(self):
        if self.training_mode == None:
            self.models['landlord'].eval()
            self.models['second_hand'].eval()
        else:
            self.models[self.training_mode].eval()

    def parameters(self, position):
        return self.models[position].parameters()

    def get_model(self, position):
        return self.models[position]

    def get_models(self):
        return self.models
