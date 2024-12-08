from copy import deepcopy
from . import move_detector as md, move_selector as ms
from .move_generator import MovesGener
import json
import random

Card2Column = {}
for i in range(1, 4 + 1):
    Card2Column[i] = i - 1
for i in range(10, 20 + 1):
    Card2Column[i] = i - 6
for i in range(23, 28 + 1):
    Card2Column[i] = i - 8

Column2Card = {value: key for key, value in Card2Column.items()}

CardTypeToIndex = {
    "spell": 0,
    "aoe_spell": 1,
    "minion": 2,
    "minion_with_burst": 3,
    "minion_increase_spell_power": 4
}
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
        if "type" not in value:
            value["type"] = "minion"
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
                               'second_hand': [],
                               'pk_dp': []}

        self.played_cards = {'landlord': [],
                             'second_hand': [],
                             'pk_dp': []}
        
        self.played_actions = {'landlord': [],
                             'second_hand': [],
                             'pk_dp': []}

        self.last_move = []
        self.last_two_moves = []

        self.num_wins = {'landlord': 0,
                         'farmer': 0}

        self.num_scores = {'landlord': 0,
                           'farmer': 0}

        self.info_sets = {'landlord': InfoSet('landlord'),
                         'second_hand': InfoSet('second_hand'),
                         'pk_dp': InfoSet('pk_dp'),}

        self.bomb_num = 0
        self.last_pid = 'landlord'
        self.round = 0
        self.scores = {
            'landlord': 0,
            'second_hand': 0,
            'pk_dp': 0,
            }
        self.deck_cards = []

    def card_play_init(self, card_play_data):
        # #  ['水宝宝鱼人', '三角测量', '流彩巨岩', '艾瑞达蛮兵', '织法者玛里苟斯', '虚灵神谕者', '立体书', '立体书', '极紫外破坏者', '麦芽岩浆', '消融元素', '艾瑞达蛮兵', '月石重拳手', '奇利亚斯豪华版3000型', '极紫外破坏者', '陨石风暴', '电击学徒', '虚灵神谕者', '麦芽岩浆', '陨石风暴', '流彩巨岩', '消融元素', '水宝宝鱼人', '伊辛迪奥斯', '月石重拳手', '电击学徒', '“焦油泥浆怪', ' 针岩图腾', '“焦油泥浆怪', '三角测量']
        # card_play_data['landlord'] = [18, 23, 10, 14, 4, 12, 24, 24, 15, 26, 11, 14, 17, 3, 15, 25, 16, 12, 26, 25, 10, 11, 18, 2, 17, 16, 13, 20, 13, 23]
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


        self.info_sets['pk_dp'].player_hand_cards = []
        self.info_sets['pk_dp'].player_deck_cards = []
        self.info_sets['pk_dp'].player_hand_cards.extend(self.info_sets['landlord'].player_hand_cards)
        self.info_sets['pk_dp'].player_deck_cards.extend(self.info_sets['landlord'].player_deck_cards)

        # for debug
        self.deck_cards = []
        self.deck_cards.extend(self.info_sets['landlord'].player_hand_cards)
        self.deck_cards.extend(self.info_sets['landlord'].player_deck_cards)
        self.get_acting_player_position()
        
        self.rival_num_on_battlefield = 0
        self.companion_num_on_battlefield = 0

        self.round = 1
        self.scores = {
            'landlord': 0,
            'second_hand': 0,
            'pk_dp': 0,
            }
        self.game_infoset = self.get_infoset()

    def game_done(self):
        if self.round >= 12 or len(self.info_sets[self.acting_player_position].player_deck_cards) == 0 or \
            abs(self.scores["landlord"] - self.scores["pk_dp"]) >= 20:
            # if one of the three players discards his hand,
            # then game is over.
            # if self.scores["landlord"] < self.scores["pk_dp"] and self.scores["landlord"] < 20:
            #     self.debug()
            self.update_num_wins_scores()
            self.game_over = True

    def debug(self):
        print ("MYWEN", self.deck_cards)
        print ("MYWEN", [HearthStone[card]["name"] for card in self.deck_cards])
        print ("MYWEN", self.scores["landlord"], self.scores["pk_dp"])
        round = 1
        for action in self.played_actions["landlord"]:
            print ("MYWEN landlord", round, [HearthStone[card]["name"] for card in action], ms.calculateScore(action, HearthStone, 0, 0, 0))
            round += 1

        round = 1
        for action in self.played_actions["pk_dp"]:
            print ("MYWEN pk_dp", round, [HearthStone[card]["name"] for card in action], ms.calculateScore(action, HearthStone, 0, 0, 0))
            round += 1

    def update_num_wins_scores(self):
        self.num_scores['landlord'] = 0
        self.num_scores['second_hand'] = 0
        self.num_scores['pk_dp'] = 0

    def get_winner(self):
        return "landlord"

    def get_bomb_num(self):
        return 0
    
    def get_scores(self):
        return self.scores

    def step(self):
        # print ("MYWEN", self.acting_player_position)
        # print ("MYWEN", self.round, self.game_infoset.legal_actions)
        # print ("MYWEN", self.info_sets[self.acting_player_position].player_hand_cards)
        if self.acting_player_position == 'pk_dp':
            scoreMax = 0
            actionMax = []
            for actionTmp in self.game_infoset.legal_actions:
                score = ms.calculateScore(actionTmp, HearthStone, self.rival_num_on_battlefield, self.companion_num_on_battlefield, len(self.info_sets[
                    self.acting_player_position].player_hand_cards))
                if score > scoreMax:
                    scoreMax = score
                    actionMax = actionTmp
            action = actionMax
        else:
            action = self.players[self.acting_player_position].act(
                self.game_infoset)
            assert action in self.game_infoset.legal_actions

        if len(action) > 0:
            self.last_pid = self.acting_player_position

        self.last_move_dict[
            self.acting_player_position] = action.copy()

        self.scores[self.acting_player_position] += ms.calculateScore(action, HearthStone, self.rival_num_on_battlefield, self.companion_num_on_battlefield, len(self.info_sets[
                    self.acting_player_position].player_hand_cards))
        
        self.card_play_action_seq.append(action)
        self.update_acting_player_hand_cards(action)

        self.played_cards[self.acting_player_position] += action
        self.played_actions[self.acting_player_position].append(action)

        self.game_done()
        if not self.game_over:
            self.get_acting_player_position()
            self.game_infoset = self.get_infoset()
    
    def get_last_move(self):
        last_move = []
        if len(self.card_play_action_seq) >= 2:
                last_move = self.card_play_action_seq[-2]
        return last_move

    def get_acting_player_position(self):
        if self.acting_player_position == 'landlord':
            self.acting_player_position = 'pk_dp'
        else:
            self.acting_player_position = 'landlord'
            self.rival_num_on_battlefield = random.randint(1, min(self.round - 1, 7)) if self.round > 1 else 0
            self.companion_num_on_battlefield = random.randint(1, min(self.round - 1, 7)) if self.round > 1 else 0
            self.round += 1
        return self.acting_player_position

    def update_acting_player_hand_cards(self, action):
        count = 1
        player_hand_cards = self.info_sets[self.acting_player_position].player_hand_cards
        if action != []:
            count = ms.newCards(action, HearthStone, len(player_hand_cards))
            for card in action:
                player_hand_cards.remove(card)

        player_deck_cards = self.info_sets[self.acting_player_position].player_deck_cards
        for card in player_deck_cards[:count]:
            if len(player_hand_cards) < 10:
                player_hand_cards.extend([card])
        self.info_sets[self.acting_player_position].player_deck_cards = player_deck_cards[count:]

    def get_legal_card_play_actions(self):
        mg = MovesGener(
            self.info_sets[self.acting_player_position].player_hand_cards)

        all_moves = mg.gen_moves()

        overload = len([card for card in self.get_last_move() if card == 19])
        moves = ms.filter_hearth_stone(all_moves, min(10, self.round) - overload, HearthStone, self.rival_num_on_battlefield, self.companion_num_on_battlefield)
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
                               'second_hand': [],
                               'pk_dp': []}

        self.played_cards = {'landlord': [],
                             'second_hand': [],
                             'pk_dp': []}
        self.played_actions = {'landlord': [],
                             'second_hand': [],
                             'pk_dp': []}
        self.last_move = []
        self.last_two_moves = []

        self.info_sets = {'landlord': InfoSet('landlord'),
                         'second_hand': InfoSet('second_hand'),
                         'pk_dp': InfoSet('pk_dp')}

        self.last_pid = 'landlord'
        self.round = 1
        self.scores = {
            'landlord': 0,
            'second_hand': 0,
            'pk_dp': 0,
            }

    def get_infoset(self): # updated, after env.step, so this will be the next env.step
        self.info_sets[
            self.acting_player_position].last_pid = self.last_pid

        self.info_sets[
            self.acting_player_position].legal_actions = \
            self.get_legal_card_play_actions()

        self.info_sets[
            self.acting_player_position].card_count_by_type = []
        self.info_sets[
            self.acting_player_position].minion_be_bursted = []
        self.info_sets[
            self.acting_player_position].spell_power_increased = []

        for action in self.info_sets[self.acting_player_position].legal_actions:
            self.info_sets[
                self.acting_player_position].card_count_by_type.append(self.cardClassification(action))
            self.info_sets[
                self.acting_player_position].minion_be_bursted.append(self.minionBeBursted(action))
            self.info_sets[
                self.acting_player_position].spell_power_increased.append(self.spellPowerIncrease(action))

        self.info_sets[
            self.acting_player_position].bomb_num = self.bomb_num

        self.info_sets[
            self.acting_player_position].last_move = self.get_last_move()

        self.info_sets[
            self.acting_player_position].last_move_dict = self.last_move_dict
        
        self.info_sets[
            self.acting_player_position].rival_num_on_battlefield = self.rival_num_on_battlefield
        
        self.info_sets[
            self.acting_player_position].companion_num_on_battlefield = self.companion_num_on_battlefield

        self.info_sets[self.acting_player_position].num_cards_left_dict = \
            {pos: len(self.info_sets[pos].player_hand_cards)
             for pos in [self.acting_player_position]}

        self.info_sets[self.acting_player_position].other_hand_cards = []
        for pos in [self.acting_player_position]:
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
             for pos in [self.acting_player_position]}

        return deepcopy(self.info_sets[self.acting_player_position])

    def cardClassification(self, action):
        result = [0] * len(CardTypeToIndex)
        for card in action:
            cardId = HearthStone[card]["cardId"]
            type = HearthStone[card]["type"]
            for key in CardTypeToIndex.keys():
                if key in type:
                    result[CardTypeToIndex[key]] += 1
        return result
    
    def spellPowerIncrease(self, action): # increase many times
        return len([card for card in action if HearthStone[card]["type"] == "minion_increase_spell_power"]) * \
        len([card for card in action if HearthStone[card]["type"].endswith("spell")])
    
    def minionBeBursted(self, action): # only burst once
        return len([card for card in action if HearthStone[card]["type"] == "minion_with_burst"]) * \
        (len([card for card in action if HearthStone[card]["type"].endswith("spell")]) > 0)

class InfoSet(object):
    """
    The game state is described as infoset, which
    includes all the information in the current situation,
    such as the hand cards of the three players, the
    historical moves, etc.
    """
    def __init__(self, player_position):
        # The player position, i.e., landlord, pk_dp, or second_hand
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
        # rival num
        self.rival_num_on_battlefield = None
        # companion num
        self.companion_num_on_battlefield = None
        # spell will be increased num this round
        self.spell_power_increased = None
        # minion_be_bursted num this round
        self.minion_be_bursted = None

        # card count by type: list size of 5
        # spell num
        # aoe_spell num
        # minion num
        # minion_with_burst num
        # minion_increase_spell_power num
        self.card_count_by_type = None

