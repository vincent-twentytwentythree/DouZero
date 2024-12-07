from copy import deepcopy
from . import move_detector as md, move_selector as ms
from .move_generator import MovesGener
import json
import random

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
                    'TOY_508': 16,
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

class GameEnv(object):

    def __init__(self, players):

        self.card_play_action_seq = []

        self.three_landlord_cards = None
        self.game_over = False

        self.acting_player_position = None
        self.player_utility_dict = None

        self.players = players

        self.last_move_dict = {'landlord': [],
                               'landlord_up': [],
                               'landlord_down': []}

        self.played_cards = {'landlord': [],
                             'landlord_up': [],
                             'landlord_down': []}

        self.last_move = []
        self.last_two_moves = []

        self.num_wins = {'landlord': 0,
                         'farmer': 0}

        self.num_scores = {'landlord': 0,
                           'farmer': 0}

        self.info_sets = {'landlord': InfoSet('landlord'),
                         'landlord_up': InfoSet('landlord_up'),
                         'landlord_down': InfoSet('landlord_down'),}

        self.bomb_num = 0
        self.last_pid = 'landlord'
        self.round = 0
        self.scores = 0

    def card_play_init(self, card_play_data):
        self.info_sets['landlord'].player_hand_cards = []
        self.info_sets['landlord'].player_deck_cards = []
        for card in card_play_data['landlord'][:3]:
            if HearthStone[card]["cost"] <= 2:
                self.info_sets['landlord'].player_hand_cards.extend([card])
            else:
                self.info_sets['landlord'].player_deck_cards.extend([card])
        for card in card_play_data['landlord'][3:6]:
            if len(self.info_sets['landlord'].player_hand_cards) < 3:
                self.info_sets['landlord'].player_hand_cards.extend([card])
            else:
                self.info_sets['landlord'].player_deck_cards.extend([card])
        self.info_sets['landlord'].player_deck_cards.extend(card_play_data['landlord'][6:])
        self.get_acting_player_position()
        
        self.rival_num = 0
        self.companion_num = 0

        self.round = 1
        self.score = 0
        self.game_infoset = self.get_infoset()

    def game_done(self):
        if self.round >= 15 or len(self.info_sets[self.acting_player_position].player_deck_cards) == 0:
            # if one of the three players discards his hand,
            # then game is over.
            self.update_num_wins_scores()
            self.game_over = True

    def update_num_wins_scores(self):
        self.num_scores['landlord'] = self.scores
        self.num_scores['landlord_up'] = 0
        self.num_scores['landlord_down'] = 0

    def get_winner(self):
        return "landlord"

    def get_bomb_num(self):
        return 0

    def step(self):
        action = self.players[self.acting_player_position].act(
            self.game_infoset)
        assert action in self.game_infoset.legal_actions

        if len(action) > 0:
            self.last_pid = self.acting_player_position

        self.last_move_dict[
            self.acting_player_position] = action.copy()

        self.rival_num = random.randint(1, min(self.round - 1, 7)) if self.round > 1 else 0
        self.companion_num = random.randint(1, min(self.round - 1, 7)) if self.round > 1 else 0
        self.scores += ms.calculateScore(action, HearthStone, self.rival_num, self.companion_num, len(self.info_sets[
                    self.acting_player_position].player_hand_cards))
        self.round += 1
        
        self.card_play_action_seq.append(action)
        self.update_acting_player_hand_cards(action)

        self.played_cards[self.acting_player_position] += action

        self.game_done()
        if not self.game_over:
            self.get_acting_player_position()
            self.game_infoset = self.get_infoset()
    
    def get_last_move(self):
        last_move = []
        if len(self.card_play_action_seq) != 0:
                last_move = self.card_play_action_seq[-1]
        return last_move

    def get_acting_player_position(self):
        self.acting_player_position = 'landlord'
        return self.acting_player_position

    def update_acting_player_hand_cards(self, action):
        if action != []:
            player_hand_cards = self.info_sets[self.acting_player_position].player_hand_cards
            player_deck_cards = self.info_sets[self.acting_player_position].player_deck_cards
            count = ms.newCards(action, HearthStone, len(player_hand_cards))

            for card in action:
                player_hand_cards.remove(card)

            player_hand_cards.extend(player_deck_cards[:count])
            self.info_sets[self.acting_player_position].player_deck_cards = player_deck_cards[count:]

    def get_legal_card_play_actions(self):
        mg = MovesGener(
            self.info_sets[self.acting_player_position].player_hand_cards)

        all_moves = mg.gen_moves()

        overload = len([card for card in self.get_last_move() if card == 19])
        moves = ms.filter_hearth_stone(all_moves, self.round - overload, HearthStone, self.rival_num, self.companion_num)
        moves = moves + [[]]

        for m in moves:
            m.sort()

        return moves

    def reset(self):
        self.card_play_action_seq = []

        self.three_landlord_cards = None
        self.game_over = False

        self.acting_player_position = None
        self.player_utility_dict = None

        self.last_move_dict = {'landlord': [],
                               'landlord_up': [],
                               'landlord_down': []}

        self.played_cards = {'landlord': [],
                             'landlord_up': [],
                             'landlord_down': []}

        self.last_move = []
        self.last_two_moves = []

        self.info_sets = {'landlord': InfoSet('landlord'),
                         'landlord_up': InfoSet('landlord_up'),
                         'landlord_down': InfoSet('landlord_down')}

        self.last_pid = 'landlord'
        self.round = 1
        self.scores = 0

    def get_infoset(self): # updated, after env.step, so this will be the next env.step
        self.info_sets[
            self.acting_player_position].last_pid = self.last_pid

        self.info_sets[
            self.acting_player_position].legal_actions = \
            self.get_legal_card_play_actions()

        self.info_sets[
            self.acting_player_position].bomb_num = self.bomb_num

        self.info_sets[
            self.acting_player_position].last_move = self.get_last_move()

        self.info_sets[
            self.acting_player_position].last_move_dict = self.last_move_dict

        self.info_sets[self.acting_player_position].num_cards_left_dict = \
            {pos: len(self.info_sets[pos].player_hand_cards)
             for pos in ['landlord']}

        self.info_sets[self.acting_player_position].other_hand_cards = []
        for pos in ['landlord']:
            if pos != self.acting_player_position:
                self.info_sets[
                    self.acting_player_position].other_hand_cards += \
                    self.info_sets[pos].player_hand_cards

        self.info_sets[self.acting_player_position].played_cards = \
            self.played_cards
        self.info_sets[self.acting_player_position].three_landlord_cards = \
            self.three_landlord_cards
        self.info_sets[self.acting_player_position].card_play_action_seq = \
            self.card_play_action_seq

        self.info_sets[
            self.acting_player_position].all_handcards = \
            {pos: self.info_sets[pos].player_hand_cards
             for pos in ['landlord']}

        return deepcopy(self.info_sets[self.acting_player_position])

class InfoSet(object):
    """
    The game state is described as infoset, which
    includes all the information in the current situation,
    such as the hand cards of the three players, the
    historical moves, etc.
    """
    def __init__(self, player_position):
        # The player position, i.e., landlord, landlord_down, or landlord_up
        self.player_position = player_position
        # The hand cands of the current player. A list.
        self.player_hand_cards = None
        # The deck cands of the current player. A list.
        self.player_deck_cards = None
        # The number of cards left for each player. It is a dict with str-->int 
        self.num_cards_left_dict = None
        # The three landload cards. A list.
        self.three_landlord_cards = None
        # The historical moves. It is a list of list
        self.card_play_action_seq = None
        # The union of the hand cards of the other two players for the current player 
        self.other_hand_cards = None
        # The legal actions for the current move. It is a list of list
        self.legal_actions = None
        # The most recent valid move
        self.last_move = None
        # The most recent two moves
        self.last_two_moves = None
        # The last moves for all the postions
        self.last_move_dict = None
        # The played cands so far. It is a list.
        self.played_cards = None
        # The hand cards of all the players. It is a dict. 
        self.all_handcards = None
        # Last player position that plays a valid move, i.e., not `pass`
        self.last_pid = None
        # The number of bombs played so far
        self.bomb_num = None
