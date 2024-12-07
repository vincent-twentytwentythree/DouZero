# return all moves that can beat rivals, moves and rival_move should be same type
import collections

def filter_hearth_stone(moves, round, hearthStone):
    legal_moves = []
    for move in moves:
        cost = 0
        for card in move:
            cost += hearthStone[card]["cost"]
        if cost <= round:
            legal_moves.extend(move)
    return legal_moves

def calculateScore(self, action, hearthStone, rival_num, companion_num):
    score = 0
    for card in action:
        # 
        if cardId == "VAC_321":
            score += 5
        elif cardId == "VAC_323t2" or cardId == "VAC_323t" or cardId == "VAC_323":
            score += rival_num
        elif cardId == "GDB_445":
            score += rival_num - companion_num
            score += hearthStone[card]["cost"]
        else:
            score += hearthStone[card]["cost"]
            cardId = hearthStone[card]["cardId"]

    for card in action:
        # 
        if cardId == "VAC_321":
            score += 5
        elif cardId == "VAC_323t2" or cardId == "VAC_323t" or cardId == "VAC_323":
            score += rival_num
        elif cardId == "GDB_445":
            score += rival_num - companion_num
            score += hearthStone[card]["cost"]
        else:
            score += hearthStone[card]["cost"]
            cardId = hearthStone[card]["cardId"]
    return score
