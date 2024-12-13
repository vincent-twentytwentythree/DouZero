from copy import deepcopy
from . import move_detector as md, move_selector as ms
from .move_generator import MovesGener
import json
import random
import numpy as np

CardTypeToIndex = {
    "spell": 0,
    "aoe_spell": 1,
    "minion": 2,
    "minion_with_burst": 3,
    "minion_increase_spell_power": 4,
}
        
CardSet = [ # size of 21
    # 0
    # 幸运币
    'GAME_005', 
    # 1 - 3
    # 橙卡
    # 伊辛迪奥斯
    'VAC_321', 
    # 奇利亚斯豪华版3000型
    'TOY_330t11', 
    # 织法者玛里苟斯
    'CS3_034', 
    
    # 4 - 7
    # 随从
    # 流彩巨岩
    'GDB_434', 
    # 消融元素
    'VAC_328', 
    # 虚灵神谕者
    'GDB_310',
    # 焦油泥浆怪
    'TOY_000',
    
    # 8 - 11
    # 艾瑞达蛮兵
    'GDB_320', 
    # 极紫外破坏者
    'GDB_901', 
    # 电击学徒
    'CS3_007',
    # 月石重拳手
    'GDB_435',
    
    # 12 - 14
    # 水宝宝鱼人
    'MIS_307',
    'MIS_307t1', 
    # 针岩图腾
    'DEEP_008', 
    
    # 15 - 20
    # 法术
    # 三角测量
    'GDB_451', 
    # 立体书
    'TOY_508',
    # 陨石风暴
    'GDB_445',
    # 麦芽岩浆
    'VAC_323',
    'VAC_323t',
    'VAC_323t2',
]

RealCard2EnvCard = {key: index for index, key in enumerate(CardSet)}
EnvCard2RealCard = {value: key for key, value in RealCard2EnvCard.items()}

#
HearthStone = {}
# Open and load the JSON file
with open("cards.json", "rb") as file:
    data = json.load(file)
    HearthStone = {RealCard2EnvCard[value["id"]]: value for i, value in enumerate(data) if value["id"] in RealCard2EnvCard}

class GameEnv(object):

    def __init__(self, players, training_mode):
        
        self.training_mode = training_mode # "landlord" or 'second_hand'

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
        self.scores_of_each_actions = {'landlord': [],
                        'second_hand': [],
                        'pk_dp': []}

        self.cost_of_each_actions = {'landlord': [],
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
        self.last_pid = self.training_mode
        self.round = 0
        self.scores = {
            'landlord': 0,
            'second_hand': 0,
            'pk_dp': 0,
            }
        self.deck_cards = []
        self.game_over_times = 0

    def getDeckCards(self):
        return self.deck_cards
    
    def getCardForFirstHand(self, card_play_data):
        self.info_sets[self.training_mode].player_hand_cards = []
        self.info_sets[self.training_mode].player_deck_cards = []

        for card in card_play_data[self.training_mode][:3]:
            if HearthStone[card]["cost"] <= 2:
                self.info_sets[self.training_mode].player_hand_cards.extend([card])
            else:
                self.info_sets[self.training_mode].player_deck_cards.extend([card])
        for card in card_play_data[self.training_mode][3:6]:
            if len(self.info_sets[self.training_mode].player_hand_cards) < 3:
                self.info_sets[self.training_mode].player_hand_cards.extend([card])
            else:
                self.info_sets[self.training_mode].player_deck_cards.extend([card])
        
        self.info_sets[self.training_mode].player_hand_cards.extend(card_play_data[self.training_mode][6:7])
        self.info_sets[self.training_mode].player_deck_cards.extend(card_play_data[self.training_mode][7:])
        
        np.random.shuffle(self.info_sets[self.training_mode].player_deck_cards)

    def getCardForSecondHand(self, card_play_data):
        self.info_sets[self.training_mode].player_hand_cards = []
        self.info_sets[self.training_mode].player_deck_cards = []

        for card in card_play_data[self.training_mode][:4]:
            if HearthStone[card]["cost"] <= 2:
                self.info_sets[self.training_mode].player_hand_cards.extend([card])
            else:
                self.info_sets[self.training_mode].player_deck_cards.extend([card])
        for card in card_play_data[self.training_mode][4:8]:
            if len(self.info_sets[self.training_mode].player_hand_cards) < 4:
                self.info_sets[self.training_mode].player_hand_cards.extend([card])
            else:
                self.info_sets[self.training_mode].player_deck_cards.extend([card])
        
        self.info_sets[self.training_mode].player_hand_cards.extend(card_play_data[self.training_mode][8:9])
        self.info_sets[self.training_mode].player_deck_cards.extend(card_play_data[self.training_mode][9:])
        self.info_sets[self.training_mode].player_hand_cards.extend([0]) # coin
        
        np.random.shuffle(self.info_sets[self.training_mode].player_deck_cards)
        
    def card_play_init(self, card_play_data):
        
        cardSetForTest = ['水宝宝鱼人', '三角测量', '流彩巨岩', '艾瑞达蛮兵', '织法者玛里苟斯', '虚灵神谕者', \
                           '立体书', '立体书', '极紫外破坏者', '麦芽岩浆', '消融元素', '艾瑞达蛮兵', '月石重拳手', \
                            '奇利亚斯豪华版3000型', '极紫外破坏者', '陨石风暴', '电击学徒', '虚灵神谕者', '麦芽岩浆', \
                            '陨石风暴', '流彩巨岩', '消融元素', '水宝宝鱼人', '伊辛迪奥斯', '月石重拳手', '电击学徒', \
                            '“焦油泥浆怪', ' 针岩图腾', '“焦油泥浆怪', '三角测量'] # MYWEN
        # card_play_data[self.training_mode] = [12, 15, 4, 8, 3, 6, 16, 16, 9, 18, 5, 8, 11, 2, 9, 17, 10, 6, 18, 17, 4, 5, 12, 1, 11, 10, 15]

        if self.training_mode == "landlord":
            self.getCardForFirstHand(card_play_data)
        elif self.training_mode == "second_hand":
            self.getCardForSecondHand(card_play_data)
        else:
            raise Exception("mode not support")

        self.info_sets['pk_dp'].player_hand_cards = []
        self.info_sets['pk_dp'].player_deck_cards = []
        self.info_sets['pk_dp'].player_hand_cards.extend(self.info_sets[self.training_mode].player_hand_cards)
        self.info_sets['pk_dp'].player_deck_cards.extend(self.info_sets[self.training_mode].player_deck_cards)

        # for debug
        self.deck_cards = []
        self.deck_cards.extend(self.info_sets[self.training_mode].player_hand_cards)
        self.deck_cards.extend(self.info_sets[self.training_mode].player_deck_cards)
        self.acting_player_position = None
        self.get_acting_player_position()
        
        self.rival_num_on_battlefield = {
            'landlord': 0,
            'second_hand': 0,
            'pk_dp': 0,
            }
        self.companion_num_on_battlefield = {
            'landlord': 0,
            'second_hand': 0,
            'pk_dp': 0,
            }
        self.companion_with_power_inprove = {
            'landlord': 0,
            'second_hand': 0,
            'pk_dp': 0,
            }
        self.companion_with_spell_burst = {
            'landlord': 0,
            'second_hand': 0,
            'pk_dp': 0,
            }

        self.round = 1
        self.scores = {
            'landlord': 0,
            'second_hand': 0,
            'pk_dp': 0,
            }
        self.game_infoset = self.get_infoset()

    def game_done(self):
        if self.round > 14 or len(self.info_sets[self.acting_player_position].player_deck_cards) == 0 or \
            abs(self.scores[self.training_mode] - self.scores["pk_dp"]) >= 30:
            # if one of the three players discards his hand,
            # then game is over.
            # if abs(self.scores[self.training_mode] - self.scores["pk_dp"]) < 5:
            # self.debug()
            self.update_num_wins_scores()
            self.game_over = True
            self.game_over_times += 1
            if self.game_over_times % 1000 == 0:
                print ("MYWEN game_over", self.game_over_times)

    def debug(self): # MYWEN
        print ("MYWEN", self.deck_cards)
        print ("MYWEN", [HearthStone[card]["name"] for card in self.deck_cards])
        print ("MYWEN", self.scores[self.training_mode], self.scores["pk_dp"])
        round = 1
        for index, action in enumerate(self.played_actions[self.training_mode]):
            print ("MYWEN ", self.training_mode, round, [HearthStone[card]["name"] for card in action], self.scores_of_each_actions[self.training_mode][index], self.cost_of_each_actions[self.training_mode][index])
            round += 1

        round = 1
        for index, action in enumerate(self.played_actions["pk_dp"]):
            print ("MYWEN pk_dp", round, [HearthStone[card]["name"] for card in action], self.scores_of_each_actions["pk_dp"][index], self.cost_of_each_actions["pk_dp"][index])
            round += 1

    def update_num_wins_scores(self):
        self.num_scores['landlord'] = 0
        self.num_scores['second_hand'] = 0
        self.num_scores['pk_dp'] = 0

    def get_winner(self):
        return self.training_mode

    def get_bomb_num(self):
        return 0
    
    def get_scores(self):
        return self.scores
    
    def getMockActionIndex(self):
        scoreMax = 0
        actionMaxIndex = 0
        for index, action in enumerate(self.game_infoset.legal_actions):
            score = self.calculateScore(action)
            if score > scoreMax:
                scoreMax = score
                actionMaxIndex = index
        return actionMaxIndex

    def filter_hearth_stone(self, all_moves):
        overload = len([card for card in self.get_last_move() if HearthStone[card]["id"] == "CS3_007"]) # MYWEN
        return ms.filter_hearth_stone(all_moves, min(10, self.round) - overload, HearthStone,
                                 self.rival_num_on_battlefield[self.acting_player_position],
                                 self.companion_num_on_battlefield[self.acting_player_position],
                                )

    def calculateScore(self, action):
        overload = len([card for card in self.get_last_move() if HearthStone[card]["id"] == "CS3_007"]) # MYWEN
        return ms.calculateScore(action, min(10, self.round) - overload, HearthStone,
                                 self.rival_num_on_battlefield[self.acting_player_position],
                                 self.companion_num_on_battlefield[self.acting_player_position],
                                 self.companion_with_power_inprove[self.acting_player_position],
                                 self.companion_with_spell_burst[self.acting_player_position],
                                 len(self.info_sets[self.acting_player_position].player_hand_cards))
        
    def cost(self, action):
        cost, _ = ms.calculateActionCost(action, HearthStone,
                            self.rival_num_on_battlefield[self.acting_player_position],
                            self.companion_num_on_battlefield[self.acting_player_position])
        return cost
    def step(self): # MYWEN todo
        # print ("MYWEN", self.acting_player_position)
        # print ("MYWEN", self.round, self.game_infoset.legal_actions)
        # print ("MYWEN", self.info_sets[self.acting_player_position].player_hand_cards)
        action = self.players[self.acting_player_position].act(
            self.game_infoset)
        assert action in self.game_infoset.legal_actions

        if len(action) > 0:
            self.last_pid = self.acting_player_position

        self.last_move_dict[
            self.acting_player_position] = action.copy()

        score_of_action = self.calculateScore(action)
        self.scores[self.acting_player_position] += score_of_action
        
        self.card_play_action_seq.append(action)
        self.update_acting_player_hand_cards(action)

        self.played_cards[self.acting_player_position] += action
        self.played_actions[self.acting_player_position].append(action)
        self.scores_of_each_actions[self.acting_player_position].extend([score_of_action])
        
        self.cost_of_each_actions[self.acting_player_position].extend([self.cost(action)])

        rival_action = self.card_play_action_seq[-2] if len(self.card_play_action_seq) >= 2 else []
        rivalCardByType = self.cardClassification(rival_action)
        cardByType = self.cardClassification(action)
        self.rival_num_on_battlefield[self.acting_player_position] = random.randint(0, rivalCardByType[CardTypeToIndex["minion"]])
        self.companion_num_on_battlefield[self.acting_player_position] = random.randint(0, cardByType[CardTypeToIndex["minion"]])
        self.companion_with_power_inprove[self.acting_player_position] = random.randint(0, min(self.companion_num_on_battlefield[self.acting_player_position], cardByType[CardTypeToIndex["minion_increase_spell_power"]]))
        self.companion_with_spell_burst[self.acting_player_position] = random.randint(0, min(self.companion_num_on_battlefield[self.acting_player_position] - self.companion_with_power_inprove[self.acting_player_position],
                                                                                             cardByType[CardTypeToIndex["minion_with_burst"]]))
        
        if self.training_mode == "landlord" and self.acting_player_position == "pk_dp":
            self.round += 1
        elif self.training_mode == "second_hand" and self.acting_player_position == "second_hand":
            self.round += 1
        self.game_done()
        if not self.game_over:
            self.get_acting_player_position()
            self.game_infoset = self.get_infoset()
    
    def get_last_move(self):
        last_move = []
        if len(self.card_play_action_seq) >= 3:
                last_move = self.card_play_action_seq[-3]
        return last_move

    def get_acting_player_position(self):
        if self.acting_player_position == self.training_mode:
            self.acting_player_position = 'pk_dp'
        elif self.acting_player_position == 'pk_dp':
            self.acting_player_position = self.training_mode
        elif self.acting_player_position == None and self.training_mode == "landlord": # 先手
            self.acting_player_position = "landlord"
        elif self.acting_player_position == None and self.training_mode == "second_hand": # 后手
            self.acting_player_position = 'pk_dp'
        else:
            raise Exception("mode not support")
        return self.acting_player_position

    def update_acting_player_hand_cards(self, action):
        count = 1
        player_hand_cards = self.info_sets[self.acting_player_position].player_hand_cards
        if action != []:
            count = ms.newCards(action, HearthStone, len(player_hand_cards))
            for card in action:
                player_hand_cards.remove(card)
                if HearthStone[card]["id"] == "VAC_323": #todo 三角测量
                    player_hand_cards.append(RealCard2EnvCard["VAC_323t"])
                elif HearthStone[card]["id"] == "VAC_323t":
                    player_hand_cards.append(RealCard2EnvCard["VAC_323t2"])
                elif HearthStone[card]["id"] == "MIS_307":
                    player_hand_cards.append(RealCard2EnvCard["MIS_307t1"])

        player_deck_cards = self.info_sets[self.acting_player_position].player_deck_cards
        for card in player_deck_cards[:count]:
            if len(player_hand_cards) < 10:
                player_hand_cards.extend([card])
        self.info_sets[self.acting_player_position].player_deck_cards = player_deck_cards[count:]
    
    def get_legal_card_play_actions(self):
        mg = MovesGener(
            self.info_sets[self.acting_player_position].player_hand_cards)

        all_moves = mg.gen_moves()

        moves = self.filter_hearth_stone(all_moves)

        # for m in moves:
        #     m.sort()

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
        self.scores_of_each_actions = {'landlord': [],
                        'second_hand': [],
                        'pk_dp': []}

        self.cost_of_each_actions = {'landlord': [],
                        'second_hand': [],
                        'pk_dp': []}
        
        self.last_move = []
        self.last_two_moves = []

        self.info_sets = {'landlord': InfoSet('landlord'),
                         'second_hand': InfoSet('second_hand'),
                         'pk_dp': InfoSet('pk_dp')}

        self.last_pid = self.training_mode
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
            self.acting_player_position].advice = []

        for action in self.info_sets[self.acting_player_position].legal_actions:
            self.info_sets[
                self.acting_player_position].card_count_by_type.append(self.cardClassification(action))
            self.info_sets[
                self.acting_player_position].advice.append(min(9, self.calculateScore(action) // 3))

        self.info_sets[
            self.acting_player_position].bomb_num = self.bomb_num

        self.info_sets[
            self.acting_player_position].last_move = self.get_last_move()

        self.info_sets[
            self.acting_player_position].last_move_dict = self.last_move_dict
        
        self.info_sets[
            self.acting_player_position].rival_num_on_battlefield = self.rival_num_on_battlefield[self.acting_player_position]
        
        self.info_sets[
            self.acting_player_position].companion_num_on_battlefield = self.companion_num_on_battlefield[self.acting_player_position]
        
        self.info_sets[
            self.acting_player_position].companion_with_power_inprove = self.companion_with_power_inprove[self.acting_player_position]
        
        self.info_sets[
            self.acting_player_position].companion_with_spell_burst = self.companion_with_spell_burst[self.acting_player_position]

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
        self.info_sets[self.acting_player_position].played_actions = \
            self.played_actions[self.acting_player_position]
        
        self.info_sets[self.acting_player_position].scores_of_each_actions = \
            self.scores_of_each_actions[self.acting_player_position]

        self.info_sets[
            self.acting_player_position].all_handcards = \
            {pos: self.info_sets[pos].player_hand_cards
             for pos in [self.acting_player_position]}

        return deepcopy(self.info_sets[self.acting_player_position])

    def cardClassification(self, action):
        result = [0] * len(CardTypeToIndex)
        for card in action:
            cardId = HearthStone[card]["id"]
            type = HearthStone[card]["type"]
            text = HearthStone[card]["text"]
            if type == "MINION":
                if "法术迸发" in text:
                    result[CardTypeToIndex["minion_with_burst"]] += 1
                if "法术伤害+" in text:
                    result[CardTypeToIndex["minion_increase_spell_power"]] += 1
                result[CardTypeToIndex["minion"]] += 1
            elif type == "SPELL":
                if "对所有敌方随从造成" in text:
                    result[CardTypeToIndex["aoe_spell"]] += 1
                result[CardTypeToIndex["spell"]] += 1
        return result

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
        # The played actions so far. It is a list.
        self.played_actions = None
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
        # companion_with_power_inprove this round
        self.companion_with_power_inprove = None
        # companion_with_spell_burst this round
        self.companion_with_spell_burst = None
        # advice, totaly 10 level
        self.advice = None

        # card count by type: list size of 5
        # spell num
        # aoe_spell num
        # minion num
        # minion_with_burst num
        # minion_increase_spell_power num
        self.card_count_by_type = None

        # scores_of_each_actions
        self.scores_of_each_actions = None

