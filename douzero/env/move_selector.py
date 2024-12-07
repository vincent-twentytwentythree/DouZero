# return all moves that can beat rivals, moves and rival_move should be same type
import collections

def filter_hearth_stone(moves, crystal, hearthStone, rival_num, companion_num):
    legal_moves = []
    for move in moves:
        cost = 0
        for card in move:
            cardId = hearthStone[card]["cardId"]
            if cardId == "GDB_320":
                cost += max(0, hearthStone[card]["cost"] - rival_num)
            else:
                cost += hearthStone[card]["cost"]
        if cost <= crystal:
            legal_moves.extend([move])
    return legal_moves

def calculateScore(action, hearthStone, rival_num, companion_num, hands_num):
    score = 0
    for card in action:
        cardId = hearthStone[card]["cardId"]
        if cardId.startswith("VAC_323"): # 麦芽岩浆
            score += min(hearthStone[card]["cost"], rival_num)
        elif cardId.startswith("GDB_445"): # 陨石风暴
            score += hearthStone[card]["cost"] - (companion_num - rival_num)
        score += hearthStone[card]["cost"]

    # 法强+1
    power_plus_count = len([hearthStone[card]["isPowerPlus"] == True for card in action])
    for card in action:
        cardId = hearthStone[card]["cardId"]
        if cardId == "TOY_508": # 立体书
            score += power_plus_count
        elif cardId.startswith("VAC_323"): # 麦芽岩浆
            score += power_plus_count * rival_num
        elif cardId.startswith("GDB_445"): # 陨石风暴
            score += power_plus_count * (companion_num - rival_num)

    # 法术迸发
    spell_count = len([hearthStone[card]["isSpell"] == True for card in action])
    for card in action:
        cardId = hearthStone[card]["cardId"]
        if cardId == "GDB_434" and spell_count > 0: # 流彩巨岩
            score += 3
        elif cardId == "GDB_310" and spell_count > 0: # 虚灵神谕者
            score += 2

    # 其他特殊效果
    for card in action:
        cardId = hearthStone[card]["cardId"]
        if cardId == "CS3_034": # 织法者玛里苟斯
            score += 10 - (hands_num - len(action))
        elif cardId == "VAC_321": # 伊辛迪奥斯
            score += 5 * 2
        elif cardId == "GDB_901" and rival_num > 0: # 极紫外破坏者
            score += 1
    return score

def newCards(action, hearthStone, hands_num):
    count = 1
    for card in action:
        cardId = hearthStone[card]["cardId"]
        if cardId == "GDB_310": # 虚灵神谕者
            spell_count = len([hearthStone[card]["isSpell"] == True for card in action])
            if spell_count > 0:
                count += 2
        elif cardId == "CS3_034": # 织法者玛里苟斯
            count += 10 - (hands_num - len(action))