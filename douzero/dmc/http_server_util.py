import os

import torch

import re

import json

from .file_writer import FileWriter
from .models import Model
from .utils import log, getDevice
from ..env.env import get_obs, deck
from ..env.game import InfoSet
from ..env.move_generator import MovesGener
from ..env import move_selector as ms

from ..env.game import CardTypeToIndex, CardSet, FullCardSet, RealCard2EnvCard, EnvCard2RealCard, HearthStone

from ..env.game import GameEnv

gameEnv = GameEnv(None, None)

#
HearthStoneByCardId = {}
# Open and load the JSON file
with open("cards.json", "rb") as file:
    data = json.load(file)
    HearthStoneByCardId = {meta["id"]: meta for i, meta in enumerate(data)}

MaxIndex = len(CardSet)

def getModel(flags):
    if not flags.actor_device_cpu or flags.training_device != 'cpu':
        if not torch.cuda.is_available() and not torch.mps.is_available():
            raise AssertionError("CUDA not available. If you have GPUs, please specify the ID after `--gpu_devices`. Otherwise, please train with CPU with `python3 train.py --actor_device_cpu --training_device cpu`")
    plogger = FileWriter(
        xpid=flags.xpid,
        xp_args=flags.__dict__,
        rootdir=flags.savedir,
    )

    # Learner model for training
    learner_model = Model(device=flags.training_device)

    # Load models if any
    for k in ['landlord', 'second_hand']:
        checkpointpath = os.path.expandvars(
            os.path.expanduser('%s/%s/%s' % (flags.savedir, flags.xpid, k+'_model.tar')))
        if flags.load_model and os.path.exists(checkpointpath):
            device = getDevice(deviceName=flags.training_device)
            checkpoint_states = torch.load(
                checkpointpath, map_location=(device)
            )
            learner_model.get_model(k).load_state_dict(checkpoint_states["model_state_dict"][k])
            stats = checkpoint_states["stats"]
            log.info(f"Resuming preempted job, current stats:\n{stats}")

    return learner_model

def get_legal_card_play_actions(crystal, player_hand_cards,
                                rival_num_on_battlefield,
                                companion_num_on_battlefield):
    mg = MovesGener(player_hand_cards, FullCardSet)

    all_moves = mg.gen_moves()

    moves = ms.filter_hearth_stone(all_moves, crystal, HearthStone,
                                rival_num_on_battlefield,
                                companion_num_on_battlefield,
                                FullCardSet
                                )

    return moves
    
def get_infoset(position,
                crystal,
                player_hand_cards,
                player_deck_cards,
                played_actions,
                rival_battle_cards,
                companion_battle_cards,
                companion_burst_cards,
                ):
    
    info_set = InfoSet(position)

    info_set.all_legal_actions = get_legal_card_play_actions(crystal,
                                                         player_hand_cards,
                                                         len(rival_battle_cards),
                                                         len(companion_battle_cards)
                                                         )
    
    info_set.legal_actions = [action for action in info_set.all_legal_actions if len(action) == 0 or max(action) < MaxIndex]

    info_set.full_player_hand_cards = player_hand_cards
    info_set.player_hand_cards = [card for card in info_set.full_player_hand_cards if card < MaxIndex]
    if len(player_deck_cards) == 0:
        _deck = deck.copy()
        for card in player_hand_cards:
            if card in _deck:
                _deck.remove(card)
        for card in [card for action in played_actions for card in action ]:
            if card in _deck:
                _deck.remove(card)
        info_set.player_deck_cards = _deck
    else:
        info_set.player_deck_cards = player_deck_cards
    info_set.last_move = played_actions[-1] if len(played_actions) > 0 else []

    info_set.rival_num_on_battlefield = len(rival_battle_cards)
        
    info_set.companion_num_on_battlefield = len(companion_battle_cards)

    info_set.companion_with_power_inprove = len([cardId for cardId in companion_battle_cards if cardId == "GDB_310"
                                                 or cardId == "CS3_007"
                                                 or cardId == "CS2_052" ])
        
    info_set.companion_with_spell_burst = len(companion_burst_cards)

    info_set.played_actions = played_actions

    info_set.card_count_by_type = []
    info_set.advice = []

    for action in info_set.legal_actions:
        info_set.card_count_by_type.append(gameEnv.cardClassification(action))
        info_set.advice.append(min(9, ms.calculateScore(action, crystal, HearthStone,
                                                        info_set.rival_num_on_battlefield,
                                                        info_set.companion_num_on_battlefield,
                                                        info_set.companion_with_power_inprove,
                                                        info_set.companion_with_spell_burst,
                                                        len(info_set.full_player_hand_cards)) // 3)) # todo
    return info_set

def toEnvCardList(cardList, filter = True):
    if filter == True:
        return [RealCard2EnvCard[card] for card in cardList if card in RealCard2EnvCard and RealCard2EnvCard[card] < MaxIndex]
    else:
        return [RealCard2EnvCard[card] for card in cardList if card in RealCard2EnvCard]

def getMockActionIndex(info_set, crystal):
    scoreMax = 0
    actionMaxIndex = 0
    for index, action in enumerate(info_set.all_legal_actions):
        score = ms.calculateScore(action, crystal, HearthStone,
                                                        info_set.rival_num_on_battlefield,
                                                        info_set.companion_num_on_battlefield,
                                                        info_set.companion_with_power_inprove,
                                                        info_set.companion_with_spell_burst,
                                                        len(info_set.full_player_hand_cards)
                                )
        if score > scoreMax and 0 not in action: # 不带硬币
            scoreMax = score
            actionMaxIndex = index
    return actionMaxIndex

def compete(actions, crystal, info_set):
    maxCost = 0
    maxScore = 0
    maxAction = []
    for action in actions:
        cost, _ = ms.calculateActionCost(action, HearthStone, info_set.rival_num_on_battlefield, info_set.companion_num_on_battlefield)
        score = ms.calculateScore(action, crystal, HearthStone,
                                                            info_set.rival_num_on_battlefield,
                                                            info_set.companion_num_on_battlefield,
                                                            info_set.companion_with_power_inprove,
                                                            info_set.companion_with_spell_burst,
                                                            len(info_set.full_player_hand_cards)
        )
        if score > maxScore or (score == maxScore and len(action) < len(maxAction)):
            maxCost = cost
            maxScore = score
            maxAction = action
    
        print ([HearthStone[card]["name"] for card in action], action, "cost: ", cost, "score: ", score)
    return maxAction, maxCost, maxScore
    
def patch(player_hand_cards, rival_battle_cards, companion_burst_cards, companion_battle_cards):
    if len(companion_burst_cards) > 0:
        player_hand_cards = [card for card in player_hand_cards if card != "GDB_445" ] # 陨石风暴
    if len(player_hand_cards) >= 5:
        player_hand_cards = [card for card in player_hand_cards if card != "CS3_034" ] # 织法者玛里苟斯
    if len(rival_battle_cards) >= 4:
        player_hand_cards = [card for card in player_hand_cards if card != "VAC_321" ] # 伊辛迪奥斯
    if len(companion_battle_cards) >= 6:
        player_hand_cards = [card for card in player_hand_cards if card != "MIS_307t1" ] # 水宝宝鱼人
    if len(companion_battle_cards) >= 4 and companion_burst_cards == 0:
        player_hand_cards = [card for card in player_hand_cards if card != "TOY_508" ] # 立体书
    return player_hand_cards

def onceCard(txt):
    current_turn_pattern = r".*在本回合.*"
    battle_cry_pattern = r".*战吼.*"
    die_cry_pattern = r".*亡语.*"
    return re.match(current_turn_pattern, txt) != None \
        or re.match(battle_cry_pattern, txt) != None \
        or re.match(die_cry_pattern, txt) != None
    
def getCoreCard(card_list):
    every_after_pattern = r".*后.*"
    every_when_pattern = r".*当.*"
    every_when_pattern_2 = r".*时.*"
    attack_plus_pattern =r".*伤害+.*"
    other_have_pattern = r".*其他.*拥有.*"
    other_get_pattern = r".*其他.*获得.*"
    near_have_pattern = r".*相邻.*拥有.*"
    near_get_pattern = r".*相邻.*获得.*"
    core_cards = {}
    for cardId in card_list:
        value = 1.0
        if cardId in HearthStoneByCardId and "text" in HearthStoneByCardId[cardId]:
            meta = HearthStoneByCardId[cardId]
            if cardId == "VAC_321":
                value += 5
            elif re.match(every_after_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif re.match(every_when_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif re.match(every_when_pattern_2, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif re.match(other_have_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 6
            elif re.match(other_get_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 6
            elif re.match(near_have_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif re.match(near_get_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif re.match(attack_plus_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
        core_cards[cardId] = value
        
    return core_cards

def getPowerPlus(companion_battle_cards):
    return len([card for card in companion_battle_cards if "text" in HearthStoneByCardId[card] and "法术伤害+" in HearthStoneByCardId[card]["text"]])
    
def predict(model, requestBody, flags):
    position = requestBody.get("position")
    round = requestBody.get("round")
    crystal = requestBody.get("crystal")
    player_hand_cards = requestBody.get('player_hand_cards', [])
    player_deck_cards = requestBody.get('player_deck_cards', [])
    played_actions = requestBody.get('played_actions', [])
    rival_battle_cards = requestBody.get('rival_battle_cards', [])
    companion_battle_cards = requestBody.get('companion_battle_cards', [])
    companion_burst_cards = requestBody.get('companion_burst_cards', [])

    if crystal == 0:
        response = {"status": "succ", "action": [], "cost": 0, "score": 0, "crystal": crystal, \
            "coreCards": getCoreCard(rival_battle_cards + companion_battle_cards + CardSet),
            "powerPlus": getPowerPlus(companion_battle_cards),
            }
        return response

    player_hand_cards = patch(player_hand_cards, rival_battle_cards, companion_burst_cards, companion_battle_cards)

    info_set = get_infoset(position,
                           crystal,
                           toEnvCardList(player_hand_cards, False),
                           toEnvCardList(player_deck_cards, False),
                           [toEnvCardList(action, True) for action in played_actions],
                           rival_battle_cards,
                           companion_battle_cards,
                           companion_burst_cards
                        )
    obs = get_obs(info_set)

    device = getDevice(deviceName=flags.training_device)
    obs_x = torch.from_numpy(obs['x_batch']).to(device)
    obs_z = torch.from_numpy(obs['z_batch']).to(device)

    with torch.no_grad():
        agent_output = model.forward(position, obs_z, obs_x, topk=3)
    _action_idx = agent_output['action'].cpu().detach().numpy().tolist()
    _action_idx_pk = getMockActionIndex(info_set, crystal=crystal)

    _action_idx.extend([_action_idx_pk])

    action, cost, score = compete([info_set.all_legal_actions[idx] for idx in _action_idx], crystal, info_set)
    realAction = [EnvCard2RealCard[card] for card in action]
    
    handCards = [HearthStone[card]["name"] for card in info_set.player_hand_cards]
    deckCards = [HearthStone[card]["name"] for card in info_set.player_deck_cards]
    actionRealname = [HearthStone[card]["name"] for card in action]
    
    print(f"handCards: {handCards} ")
    print(f"deckCards: {deckCards} ")
    print(f"action: {realAction}")
    print(f"action: {actionRealname}")
    print(f"cost: {cost}, score: {score}")

    response = {"status": "succ", "action": realAction, "cost": cost, "score": score, "crystal": crystal, \
                "coreCards": getCoreCard(rival_battle_cards + companion_battle_cards + CardSet),
                "powerPlus": getPowerPlus(companion_battle_cards),
                }
    if flags.debug:
        if 'TOY_508' in player_hand_cards and len(rival_battle_cards) > 0:
            response["action"] = ['TOY_508']
        elif 'TOY_508' in realAction:
            realAction.remove('TOY_508')
    return response