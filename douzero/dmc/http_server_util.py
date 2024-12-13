import os

import torch

from .file_writer import FileWriter
from .models import Model
from .utils import log, getDevice
from ..env.env import get_obs, deck
from ..env.game import InfoSet
from ..env.move_generator import MovesGener
from ..env import move_selector as ms

from ..env.game import CardTypeToIndex, CardSet, RealCard2EnvCard, EnvCard2RealCard, HearthStone

from ..env.game import GameEnv

gameEnv = GameEnv(None, None)

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
    mg = MovesGener(player_hand_cards)

    all_moves = mg.gen_moves()

    moves = ms.filter_hearth_stone(all_moves, crystal, HearthStone,
                                rival_num_on_battlefield,
                                companion_num_on_battlefield,
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

    info_set.legal_actions = get_legal_card_play_actions(crystal,
                                                         player_hand_cards,
                                                         len(rival_battle_cards),
                                                         len(companion_battle_cards)
                                                         )
    info_set.player_hand_cards = player_hand_cards
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
                                                        len(info_set.player_hand_cards)) // 3)) # todo
    return info_set

def toEnvCardList(cardList):
    return [RealCard2EnvCard[card] for card in cardList if card in RealCard2EnvCard] # todo

def getMockActionIndex(info_set, crystal):
    scoreMax = 0
    actionMaxIndex = 0
    for index, action in enumerate(info_set.legal_actions):
        score = ms.calculateScore(action, crystal, HearthStone,
                                                        info_set.rival_num_on_battlefield,
                                                        info_set.companion_num_on_battlefield,
                                                        info_set.companion_with_power_inprove,
                                                        info_set.companion_with_spell_burst,
                                                        len(info_set.player_hand_cards)
                                )
        if score > scoreMax:
            scoreMax = score
            actionMaxIndex = index
    return actionMaxIndex

def predict(model, requestBody, flags):
    position = requestBody.get("position")
    crystal = requestBody.get("crystal")
    player_hand_cards = requestBody.get('player_hand_cards', [])
    player_deck_cards = requestBody.get('player_deck_cards', [])
    played_actions = requestBody.get('played_actions', [])
    rival_battle_cards = requestBody.get('rival_battle_cards', [])
    companion_battle_cards = requestBody.get('companion_battle_cards', [])
    companion_burst_cards = requestBody.get('companion_burst_cards', [])
    info_set = get_infoset(position,
                           crystal,
                           toEnvCardList(player_hand_cards),
                           toEnvCardList(player_deck_cards),
                           [toEnvCardList(action) for action in played_actions],
                           rival_battle_cards,
                           companion_battle_cards,
                           companion_burst_cards
                        )
    obs = get_obs(info_set)


    if position != "pk_dp":
        device = getDevice(deviceName=flags.training_device)
        obs_x = torch.from_numpy(obs['x_batch']).to(device)
        obs_z = torch.from_numpy(obs['z_batch']).to(device)

        with torch.no_grad():
            agent_output = model.forward(position, obs_z, obs_x)
        _action_idx = int(agent_output['action'].cpu().detach().numpy())
    else:
        _action_idx = getMockActionIndex(info_set, crystal=crystal)
    action = obs['legal_actions'][_action_idx]
    cost, _ = ms.calculateActionCost(action, HearthStone, len(rival_battle_cards), len(companion_battle_cards))
    score = ms.calculateScore(action, crystal, HearthStone,
                                                        info_set.rival_num_on_battlefield,
                                                        info_set.companion_num_on_battlefield,
                                                        info_set.companion_with_power_inprove,
                                                        info_set.companion_with_spell_burst,
                                                        len(player_hand_cards)
                            )
    realAction = [EnvCard2RealCard[card] for card in action]
    
    handCards = [HearthStone[card]["name"] for card in info_set.player_hand_cards]
    deckCards = [HearthStone[card]["name"] for card in info_set.player_deck_cards]
    action = [HearthStone[card]["name"] for card in action]
    print(f"handCards: {handCards} ")
    print(f"deckCards: {deckCards} ")
    print(f"action: {action}, cost: {cost}, score: {score} ")
    return realAction