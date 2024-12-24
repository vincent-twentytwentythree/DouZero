## 引用
如果您用到我们的项目，请添加以下引用：

Zha, Daochen et al. “DouZero: Mastering DouDizhu with Self-Play Deep Reinforcement Learning.” ICML (2021).

## 安装
训练部分的代码是基于GPU设计的，因此如果想要训练模型，您需要先安装CUDA。安装步骤可以参考[官网教程](https://docs.nvidia.com/cuda/index.html#installation-guides)。对于评估部分，CUDA是可选项，您可以使用CPU进行评估。

首先，克隆本仓库：
```
git clone https://github.com/kwai/DouZero.git
```

确保您已经安装好Python 3.6及以上版本，然后安装依赖：
```
cd douzero
pip3 install -r requirements.txt
```
注意，Windows用户只能用CPU来模拟。

## 训练
假定您至少拥有一块可用的GPU，运行
```
python3 train.py
```
这会使用一块GPU训练。如果需要用多个GPU训练，使用以下参数：
*   `--gpu_devices`: 用作训练的GPU设备名
*   `--num_actor_devices`: 被用来进行模拟（如自我对弈）的GPU数量
*   `--num_actors`: 每个设备的演员进程数
*   `--training_device`: 用来进行模型训练的设备

例如，如果我们拥有4块GPU，我们想用前3个GPU进行模拟，每个GPU拥有15个演员，而使用第四个GPU进行训练，我们可以运行以下命令：
```
python3 train.py --gpu_devices 0,1,2,3 --num_actor_devices 3 --num_actors 15 --training_device 3
```
如果用CPU进行训练和模拟（Windows用户只能用CPU进行模拟），用以下参数：
*   `--training_device cpu`: 用CPU来训练
*   `--actor_device_cpu`: 用CPU来模拟

例如，用以下命令完全在CPU上运行：
```
python3 train.py --actor_device_cpu --training_device cpu
```
以下命令仅仅用CPU来跑模拟：
```
python3 train.py --actor_device_cpu
```

其他定制化的训练配置可以参考以下可选项：
```
--xpid XPID           实验id（默认值：douzero）
--save_interval SAVE_INTERVAL
                      保存模型的时间间隔（以分钟为单位）
--objective {adp,wp}  使用ADP或者WP作为奖励（默认值：ADP）
--actor_device_cpu    用CPU进行模拟
--actor_device_mps    用MPS进行模拟
--gpu_devices GPU_DEVICES
                      用作训练的GPU设备名
--num_actor_devices NUM_ACTOR_DEVICES
                      被用来进行模拟（如自我对弈）的GPU数量
--num_actors NUM_ACTORS
                      每个设备的演员进程数
--training_device TRAINING_DEVICE
                      用来进行模型训练的设备。`cpu`表示用CPU训练
--load_model          读取已有的模型
--disable_checkpoint  禁用保存检查点
--savedir SAVEDIR     实验数据存储跟路径
--total_frames TOTAL_FRAMES
                      Total environment frames to train for
--exp_epsilon EXP_EPSILON
                      探索概率
--batch_size BATCH_SIZE
                      训练批尺寸
--unroll_length UNROLL_LENGTH
                      展开长度（时间维度）
--num_buffers NUM_BUFFERS
                      共享内存缓冲区的数量
--num_threads NUM_THREADS
                      学习者线程数
--max_grad_norm MAX_GRAD_NORM
                      最大梯度范数
--learning_rate LEARNING_RATE
                      学习率
--alpha ALPHA         RMSProp平滑常数
--momentum MOMENTUM   RMSProp momentum
--epsilon EPSILON     RMSProp epsilon
```
## 启动http服务
* 套牌: AAECAaoIBLWKBJyeBsekBr2+Bg3q5wPBnwaopwakwAamwAbR0AaX4QaY4QaY4gb44gbk6gbt6gaN+AYAAQP0swbHpAb3swbHpAbu3gbHpAYAAA==
* 复制先手模型landlord_model.tar to douzero_checkpoints/douzero/landlord_model.tar
* 复制后手模型second_hand_model.tar to douzero_checkpoints/douzero/second_hand_model.tar
* python http_server.py --gpu_devices 0 --num_actor_devices 1 --num_actors 6 --training_device 0 --load_model --save_interval 10

## 接口
```json
request sample
{
  "position": "second_hand", # 先手 landlord 后手 second_hand
  "round": 10, # 回合数
  "crystal": 9, # 可用水晶数
  "player_hand_cards": [ # 手牌
    "DMF_002",
    "GDB_310",
    "TOY_000",
    "GDB_310",
    "GDB_435"
  ],
  "player_deck_cards": [], # 牌库
  "played_actions": [ # 每一回合打出的牌
    [
      "MIS_307"
    ],
    [
      "CS3_007",
      "TOY_508"
    ],
    [
      "MIS_307",
      "TOY_000"
    ],
    [
      "GDB_901",
      "CS3_007"
    ],
    [
      "DEEP_008"
    ],
    [
      "GDB_320",
      "TOY_508"
    ],
    [],
    [
      "GDB_445",
      "GDB_451"
    ],
    []
  ],
  "rival_battle_cards": [ # 敌方战场上随从牌
    "VAC_702",
    "ONY_001t",
    "ONY_001t",
    "ONY_001t",
    "ONY_001t"
  ],
  "companion_battle_cards": [ # 友方战场上随从牌
    "CS3_007",
    "GDB_310"
  ],
  "companion_burst_cards": [] # 友方战场上没有触发法术迸发的随从牌
}

response
HTTP/1.0 200 OK
Server: BaseHTTP/0.6 Python/3.12.4
Date: Tue, 24 Dec 2024 14:45:15 GMT
Content-type: application/json

{
  "status": "succ", # 处理成功 or error
  "action": [ # 下回合出牌
    "DMF_002"
  ], 
  "cost": 9, # 本次出牌的总费用
  "score": 9, # 本次出牌参考得分
  "crystal": 9, # 本回合能用的总水晶数
  "coreCards": { # 敌方随从及友方随从参考价值
    "VAC_702": 0.0,
    "ONY_001t": 0.0,
    "CS3_007": 2.0,
    "GDB_310": 2.0,
    "GAME_005": 0.0,
    "VAC_321": 5.0,
    "TOY_330t11": 0.0,
    "CS3_034": 0.0,
    "GDB_434": 0.0,
    "VAC_328": 0.0,
    "TOY_000": 0.0,
    "GDB_320": 0.0,
    "GDB_901": 0.0,
    "GDB_435": 0.0,
    "MIS_307": 0.0,
    "MIS_307t1": 0.0,
    "DEEP_008": 2.0,
    "GDB_451": 0.0,
    "TOY_508": 2.0,
    "GDB_445": 2.0,
    "VAC_323": 2.0,
    "VAC_323t": 2.0,
    "VAC_323t2": 2.0
  },
  "powerPlus": 2 # 出牌前友方战场上随从法强伤害总计增加2
}

