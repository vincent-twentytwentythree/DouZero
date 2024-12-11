# return all moves that can beat rivals, moves and rival_move should be same type
import collections

def calculateCost(move, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield):
    cost = 0
    minion = companion_num_on_battlefield
    for card in move:
        cardId = hearthStone[card]["id"]
        if cardId == "GDB_320": # 艾瑞达蛮兵
            cost += max(0, hearthStone[card]["cost"] - rival_num_on_battlefield)
        elif cardId == "GAME_005": # 硬币 todo
            cost -= 1
        elif cardId == "TOY_330t11": # 奇利亚斯需要特殊算费用
            cost += 9
        else:
            cost += hearthStone[card]["cost"]
        if hearthStone[card]["type"] == "MINION":
            minion += 1
    return cost, minion

def filter_hearth_stone(moves, crystal, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield):
    legal_moves = []
    for move in moves:
        cost, minion = calculateCost(move, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield)
        if cost <= crystal and minion <= 7:
            legal_moves.extend([move])
    return legal_moves

def calculateScore(action, crystal, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield,
                   companion_with_power_inprove,
                   companion_with_spell_burst,
                   hands_num):
    score = 0
    for card in action:
        cardId = hearthStone[card]["id"]
        if cardId.startswith("VAC_323"): # 麦芽岩浆
            score += min(hearthStone[card]["cost"], rival_num_on_battlefield)
        elif cardId.startswith("GDB_445"): # 陨石风暴
            score += hearthStone[card]["cost"] + (rival_num_on_battlefield - companion_num_on_battlefield)
        elif cardId == "TOY_330t11": # 奇利亚斯需要特殊算费用
            score += 9
        else:
            score += hearthStone[card]["cost"]

    # 法强+1
    power_plus_count = len([card for card in action if "法术伤害+" in hearthStone[card]["text"] ]) + companion_with_power_inprove
    for card in action:
        cardId = hearthStone[card]["id"]
        if cardId == "TOY_508": # 立体书
            score += power_plus_count
        elif cardId.startswith("VAC_323"): # 麦芽岩浆
            score += power_plus_count * rival_num_on_battlefield
        elif cardId.startswith("GDB_445"): # 陨石风暴
            score += companion_with_power_inprove * (rival_num_on_battlefield - companion_num_on_battlefield)

    # 法术迸发
    countSpell = len([ card for card in action if hearthStone[card]["type"] == "SPELL" ]) #
    score += (countSpell > 0) * companion_with_spell_burst * 2 # hard code MYWEN
    countSpellWithoutCoin = len([ card for card in action if hearthStone[card]["type"] == "SPELL" and hearthStone[card]["id"] != "GAME_005" and hearthStone[card]["id"] != "GDB_445" ]) # 硬币有时候不能触发 todo
    for card in action:
        cardId = hearthStone[card]["id"]
        if cardId == "GDB_434": # 流彩巨岩
            score += 3 * (countSpellWithoutCoin > 0)
        elif cardId == "GDB_310": # 虚灵神谕者
            score += 2 * (countSpellWithoutCoin > 0)

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