"""
This file includes the torch models. We wrap the three
models into one class for convenience.
"""

import numpy as np

import torch
from torch import nn

import json

RealCard2EnvCard = {
                    # 幸运币
                    'GAME_005': 1, 

                    # 橙卡
                    # 伊辛迪奥斯
                    'VAC_321': 2, 
                    # 奇利亚斯豪华版3000型
                    'TOY_330t11': 3, 
                    # 织法者玛里苟斯
                    'CS3_034': 4, 

                    # 随从
                    # 流彩巨岩
                    'GDB_434': 10, 
                    # 消融元素
                    'VAC_328': 11, 
                    # 虚灵神谕者
                    'GDB_310': 12,
                    # 焦油泥浆怪
                    'TOY_000': 13,
                    # 艾瑞达蛮兵
                    'GDB_320': 14, 
                    # 极紫外破坏者
                    'GDB_901': 15, 
                    # 点击学徒
                    'CS3_007': 16,
                    # 月石重拳手
                    'GDB_435': 17,
                    # 水宝宝鱼人
                    'MIS_307': 18,
                    'MIS_307t1': 19, 
                    # 针岩图腾
                    'DEEP_008': 20, 

                    # 法术
                    # 三角测量
                    'GDB_451': 23, 
                    # 立体书
                    'TOY_508': 24,
                    # 陨石风暴
                    'GDB_445': 25,
                    # 麦芽岩浆
                    'VAC_323': 26,
                    'VAC_323t': 27,
                    'VAC_323t2': 28,

                    }

EnvCard2RealCard = {value: key for key, value in RealCard2EnvCard.items()}

#
HearthStone = {}
# Open and load the JSON file
with open("hearthstone.json", "rb") as file:
    data = json.load(file)
    for i, value in enumerate(data):
        if "isSpell" not in value:
            value["isSpell"] = False
        if "isPowerPlus" not in value:
            value["isPowerPlus"] = False
    HearthStone = {RealCard2EnvCard[value["cardId"]]: value for i, value in enumerate(data) if value["cardId"] in RealCard2EnvCard}

class LandlordLstmModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(120, 128, batch_first=True)
        self.dense1 = nn.Linear(40 * 4 + 128, 512)
        self.dense2 = nn.Linear(512, 512)
        self.dense3 = nn.Linear(512, 512)
        self.dense4 = nn.Linear(512, 512)
        self.dense5 = nn.Linear(512, 512)
        self.dense6 = nn.Linear(512, 1)

    def forward(self, z, x, return_value=False, flags=None):
        lstm_out, (h_n, _) = self.lstm(z)
        lstm_out = lstm_out[:,-1,:]
        x = torch.cat([lstm_out,x], dim=-1)
        x = self.dense1(x)
        x = torch.relu(x)
        x = self.dense2(x)
        x = torch.relu(x)
        x = self.dense3(x)
        x = torch.relu(x)
        x = self.dense4(x)
        x = torch.relu(x)
        x = self.dense5(x)
        x = torch.relu(x)
        x = self.dense6(x)
        if return_value:
            return dict(values=x)
        else:
            if flags is not None and flags.exp_epsilon > 0 and np.random.rand() < flags.exp_epsilon:
                action = torch.randint(x.shape[0], (1,))[0]
            else:
                action = torch.argmax(x,dim=0)[0]
            return dict(action=action)

class FarmerLstmModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(120, 128, batch_first=True)
        self.dense1 = nn.Linear(484 + 128, 512)
        self.dense2 = nn.Linear(512, 512)
        self.dense3 = nn.Linear(512, 512)
        self.dense4 = nn.Linear(512, 512)
        self.dense5 = nn.Linear(512, 512)
        self.dense6 = nn.Linear(512, 1)

    def forward(self, z, x, return_value=False, flags=None):
        lstm_out, (h_n, _) = self.lstm(z)
        lstm_out = lstm_out[:,-1,:]
        x = torch.cat([lstm_out,x], dim=-1)
        x = self.dense1(x)
        x = torch.relu(x)
        x = self.dense2(x)
        x = torch.relu(x)
        x = self.dense3(x)
        x = torch.relu(x)
        x = self.dense4(x)
        x = torch.relu(x)
        x = self.dense5(x)
        x = torch.relu(x)
        x = self.dense6(x)
        if return_value:
            return dict(values=x)
        else:
            if flags is not None and flags.exp_epsilon > 0 and np.random.rand() < flags.exp_epsilon:
                action = torch.randint(x.shape[0], (1,))[0]
            else:
                action = torch.argmax(x,dim=0)[0]
            return dict(action=action)

class RandomModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.dense6 = nn.Linear(512, 1)

    def forward(self, z, x, return_value=False, flags=None):
        if return_value:
            return dict(values=torch.zeros(x.shape))
        else:
            action = torch.randint(x.shape[0], (1,))[0]
            return dict(action=action)
        
class DPModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.dense6 = nn.Linear(512, 1)

    def forward(self, z, x, return_value=False, flags=None):
        if return_value:
            return dict(values=torch.zeros(x.shape))
        else:
            action = torch.randint(x.shape[0], (1,))[0]
            return dict(action=action)

# Model dict is only used in evaluation but not training
model_dict = {}
model_dict['landlord'] = LandlordLstmModel
model_dict['second_hand'] = FarmerLstmModel
model_dict['pk_dp'] = DPModel

class Model:
    """
    The wrapper for the three models. We also wrap several
    interfaces such as share_memory, eval, etc.
    """
    def __init__(self, device=0):
        self.models = {}
        if not device == "cpu":
            device = 'cuda:' + str(device)
        self.models['landlord'] = LandlordLstmModel().to(torch.device(device))
        self.models['second_hand'] = FarmerLstmModel().to(torch.device(device))
        self.models['pk_dp'] = DPModel().to(torch.device(device))

    def forward(self, position, z, x, training=False, flags=None):
        model = self.models[position]
        return model.forward(z, x, training, flags)

    def share_memory(self):
        self.models['landlord'].share_memory()
        self.models['second_hand'].share_memory()
        self.models['pk_dp'].share_memory()

    def eval(self):
        self.models['landlord'].eval()
        self.models['second_hand'].eval()
        self.models['pk_dp'].eval()

    def parameters(self, position):
        return self.models[position].parameters()

    def get_model(self, position):
        return self.models[position]

    def get_models(self):
        return self.models
