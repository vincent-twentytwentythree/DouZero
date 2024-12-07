from douzero.env.utils import MIN_SINGLE_CARDS, MIN_PAIRS, MIN_TRIPLES, select
import collections
from itertools import combinations

class MovesGener(object):
    """
    This is for generating the possible combinations
    """
    def __init__(self, cards_list):
        self.cards_list = cards_list
        self.cards_dict = collections.defaultdict(int)

        for i in self.cards_list:
            self.cards_dict[i] += 1

    # generate all possible moves from given cards
    def gen_moves(self):
        all_combinations = []
        for r in range(1, len(self.cards_list) + 1):
            all_combinations.extend(combinations(self.cards_list, r))
        return all_combinations
