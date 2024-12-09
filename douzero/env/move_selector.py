# return all moves that can beat rivals, moves and rival_move should be same type
import collections

def filter_hearth_stone(moves, crystal, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield):
    legal_moves = []
    for move in moves:
        cost = 0
        for card in move:
            cardId = hearthStone[card]["id"]
            if cardId == "GDB_320":
                cost += max(0, hearthStone[card]["cost"] - rival_num_on_battlefield)
            else:
                cost += hearthStone[card]["cost"]
        if cost <= crystal:
            legal_moves.extend([move])
    return legal_moves

def calculateScore(action, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield, hands_num):
    score = 0
    for card in action:
        cardId = hearthStone[card]["id"]
        if cardId.startswith("VAC_323"): # 麦芽岩浆
            score += min(hearthStone[card]["cost"], rival_num_on_battlefield)
        elif cardId.startswith("GDB_445"): # 陨石风暴
            score += hearthStone[card]["cost"] + (rival_num_on_battlefield - companion_num_on_battlefield)
        else:
            score += hearthStone[card]["cost"]

    # 法强+1
    power_plus_count = len([card for card in action if "法术伤害+" in hearthStone[card]["text"] ])
    for card in action:
        cardId = hearthStone[card]["id"]
        if cardId == "TOY_508": # 立体书
            score += power_plus_count
        elif cardId.startswith("VAC_323"): # 麦芽岩浆
            score += power_plus_count * rival_num_on_battlefield
        elif cardId.startswith("GDB_445"): # 陨石风暴
            score += power_plus_count * (rival_num_on_battlefield - companion_num_on_battlefield)

    # 法术迸发
    spell_count = len([ card for card in action if hearthStone[card]["type"] == "SPELL" ])
    for card in action:
        cardId = hearthStone[card]["id"]
        if cardId == "GDB_434" and spell_count > 0: # 流彩巨岩
            score += 3
        elif cardId == "GDB_310" and spell_count > 0: # 虚灵神谕者
            score += 2

    # 其他特殊效果
    for card in action:
        cardId = hearthStone[card]["id"]
        if cardId == "CS3_034": # 织法者玛里苟斯
            score += 10 - (hands_num - len(action))
        elif cardId == "VAC_321": # 伊辛迪奥斯
            score += 5 * 2
        elif cardId == "GDB_901" and rival_num_on_battlefield > 0: # 极紫外破坏者
            score += 1
    return score

def newCards(action, hearthStone, hands_num):
    count = 1
    for card in action:
        cardId = hearthStone[card]["id"]
        if cardId == "GDB_310": # 虚灵神谕者
            spell_count = len([card for card in action if hearthStone[card]["type"].endswith("spell")])
            if spell_count > 0:
                count += 2
        elif cardId == "CS3_034": # 织法者玛里苟斯
            count += 10 - (hands_num - len(action))
    return count