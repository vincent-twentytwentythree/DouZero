# return all moves that can beat rivals, moves and rival_move should be same type
import collections

def calculateCardCost(card, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield):
    cardId = hearthStone[card]["id"]
    if cardId == "GDB_320": # 艾瑞达蛮兵
        return max(0, hearthStone[card]["cost"] - rival_num_on_battlefield)
    elif cardId == "TOY_330t11": # 奇利亚斯需要特殊算费用
        return 9
    else:
        return hearthStone[card]["cost"]

def calculateActionCost(move, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield):
    cost = 0
    minion = companion_num_on_battlefield
    for card in move:
        if hearthStone[card]["type"] == "MINION": # todo for 陨石风暴
            minion += 1
        cost += calculateCardCost(card, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield)
    return cost, minion

def repeatCard(move, CardSet):
    move_list = []
    if CardSet["MIS_307"] in move: # 水宝宝鱼人
        move_list.append([CardSet["MIS_307t1"]] + move)

def filter_hearth_stone(moves, crystal, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield, CardSet=None):
    legal_moves = []
    for move in moves:
        cost, minion = calculateActionCost(move, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield)
        coin = len([ card for card in move if hearthStone[card]["id"] == "GAME_005" ])
        if cost <= crystal + coin and minion <= 7:
            legal_moves.extend([playCardsWithOrder(move, crystal, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield)])
    return legal_moves

def playCardsWithOrder(action, crystal, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield):
    playList = [
        "GAME_005", # coin
        "GDB_445", # 陨石风暴
        "MIS_307",
        "MIS_307t", 
        "MINION",
        "SPELL",
    ]
    
    playOrder = {value: index for index, value in enumerate(playList)}
    
    sorted_cards = sorted(action, key=lambda card: playOrder[hearthStone[card]["id"]] if hearthStone[card]["id"] in playOrder else playOrder[hearthStone[card]["type"]])
    
    # if 0 in action and 4 in action and 16 in action and crystal >= 4:
    #     print ("DEBUG start", sorted_cards)
    cost = 0
    coin = 0
    cardsWithOrder = []
    for card in sorted_cards:
        cost += calculateCardCost(card, hearthStone, rival_num_on_battlefield, companion_num_on_battlefield)
        while cost > crystal and coin > 0:
            coin -= 1
            crystal += 1
            cardsWithOrder.extend([0]) # add coin
        if card == 0: # coin
            coin += 1
        else:
            cardsWithOrder.extend([card])
            
    if coin > 0:
        cardsWithOrder.extend([0] * coin)
    # if 0 in action and 4 in action and 16 in action and crystal >= 4:
    #     print ("DEBUG end", cardsWithOrder)
    return cardsWithOrder
    
def calculateScore(action, crystal, hearthStone, 
                   rival_num_on_battlefield,
                   companion_num_on_battlefield,
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
    if countSpell > 0:
        lastSpellIndex = [ index for index, card in enumerate(action) if hearthStone[card]["type"] == "SPELL" ][-1]
        for index, card in enumerate(action):
            if index >= lastSpellIndex:
                break;
            cardId = hearthStone[card]["id"]
            if cardId == "GDB_434": # 流彩巨岩
                score += 3
            elif cardId == "GDB_310": # 虚灵神谕者
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