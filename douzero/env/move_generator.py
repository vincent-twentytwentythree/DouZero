from douzero.env.utils import MIN_SINGLE_CARDS, MIN_PAIRS, MIN_TRIPLES, select
import collections
from itertools import combinations

class MovesGener(object):
    """
    This is for generating the possible combinations
    """
    def __init__(self, cards_list, Cardset):
        self.cards_list = []
        self.CardSet = Cardset

        for card in cards_list:
            self.cards_list.extend([card])
            if Cardset[card] == "VAC_323": # 麦芽岩浆
                self.cards_list.extend([card + 1])
                self.cards_list.extend([card + 2])
            if Cardset[card] == "VAC_323t": # 麦芽岩浆
                self.cards_list.extend([card + 1])

    # generate all possible moves from given cards
    def gen_moves(self):
        all_combinations = []
        for r in range(0, len(self.cards_list) + 1):
            actions_list = [list(tup) for tup in combinations(self.cards_list, r)]
            actions_list = [action for action in actions_list if 17 not in action or 20 not in action] # 陨石风暴 和 麦芽岩浆 不要一起放
            all_combinations.extend(actions_list)
            for action in actions_list:
                if 12 in action: # 水宝宝鱼人
                    all_combinations.append(action + [13]) # 巨型
        return all_combinations
