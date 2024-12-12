from collections import Counter
import numpy as np

from douzero.env.game import GameEnv, HearthStone, CardTypeToIndex

NumOnes2Array = {0: np.array([0, 0]),
                 1: np.array([1, 0]),
                 2: np.array([1, 1]),
                 3: np.array([1, 1]),
                 4: np.array([1, 1]),
                 5: np.array([1, 1]),
                 6: np.array([1, 1]),
                 }

deck = []

# 法术
for i in range(15, 18 + 1):
    deck.extend([i for _ in range(2)])

# 随从
for i in range(4, 12 + 1):
    deck.extend([i for _ in range(2)])
deck.extend([1, 2, 3, 14])

class Env:
    """
    Doudizhu multi-agent wrapper
    """
    def __init__(self, objective):
        """
        Objective is wp/adp/logadp. It indicates whether considers
        bomb in reward calculation. Here, we use dummy agents.
        This is because, in the orignial game, the players
        are `in` the game. Here, we want to isolate
        players and environments to have a more gym style
        interface. To achieve this, we use dummy players
        to play. For each move, we tell the corresponding
        dummy player which action to play, then the player
        will perform the actual action in the game engine.
        """
        self.objective = objective

        # Initialize players
        # We use three dummy player for the target position
        self.players = {}
        for position in ['landlord', 'second_hand', 'pk_dp']:
            self.players[position] = DummyAgent(position)

        # Initialize the internal environment
        self._env = GameEnv(self.players)

        self.infoset = None

    def getDeckCards(self):
        return self._env.getDeckCards()
    
    def getMockActionIndex(self):
        return self._env.getMockActionIndex()
    
    def reset(self):
        """
        Every time reset is called, the environment
        will be re-initialized with a new deck of cards.
        This function is usually called when a game is over.
        """
        self._env.reset()

        # Randomly shuffle the deck
        _deck = deck.copy()
        np.random.shuffle(_deck)
        card_play_data = {'landlord': _deck[:],
                          'second_hand': [],
                          'pk_dp': [],
                          'three_landlord_cards': [],
                          }

        # Initialize the cards
        self._env.card_play_init(card_play_data)
        self.infoset = self._game_infoset

        return get_obs(self.infoset)

    def step(self, action): # MYWEN
        """
        Step function takes as input the action, which
        is a list of integers, and output the next obervation,
        reward, and a Boolean variable indicating whether the
        current game is finished. It also returns an empty
        dictionary that is reserved to pass useful information.
        """
        assert action in self.infoset.legal_actions
        self.players[self._acting_player_position].set_action(action)
        self._env.step()
        self.infoset = self._game_infoset
        done = False
        reward = 0.0
        if self._game_over:
            done = True
            reward = self._get_reward()
            obs = None
        else:
            obs = get_obs(self.infoset)
        return obs, reward, done, {}

    def _get_reward(self):
        """
        This function is called in the end of each
        game. It returns either 1/-1 for win/loss,
        or ADP, i.e., every bomb will double the score.
        """
        winner = self._game_winner
        scores = self._game_scores
        if self.objective == 'adp':
            return scores["landlord"] - scores["pk_dp"]
        else:
            return 1.0 if scores["landlord"] > scores["pk_dp"] else -1.0

    @property
    def _game_infoset(self):
        """
        Here, inforset is defined as all the information
        in the current situation, incuding the hand cards
        of all the players, all the historical moves, etc.
        That is, it contains perferfect infomation. Later,
        we will use functions to extract the observable
        information from the views of the three players.
        """
        return self._env.game_infoset

    @property
    def _game_bomb_num(self):
        """
        The number of bombs played so far. This is used as
        a feature of the neural network and is also used to
        calculate ADP.
        """
        return self._env.get_bomb_num()
    
    
    @property
    def _game_scores(self):
        """
        The number of bombs played so far. This is used as
        a feature of the neural network and is also used to
        calculate ADP.
        """
        return self._env.get_scores()

    @property
    def _game_winner(self):
        """ A string of landlord/peasants
        """
        return self._env.get_winner()

    @property
    def _acting_player_position(self):
        """
        The player that is active. It can be landlord,
        landlod_down, or second_hand.
        """
        return self._env.acting_player_position

    @property
    def _game_over(self):
        """ Returns a Boolean
        """
        return self._env.game_over

class DummyAgent(object):
    """
    Dummy agent is designed to easily interact with the
    game engine. The agent will first be told what action
    to perform. Then the environment will call this agent
    to perform the actual action. This can help us to
    isolate environment and agents towards a gym like
    interface.
    """
    def __init__(self, position):
        self.position = position
        self.action = None

    def act(self, infoset):
        """
        Simply return the action that is set previously.
        """
        assert self.action in infoset.legal_actions
        return self.action

    def set_action(self, action):
        """
        The environment uses this function to tell
        the dummy agent what to do.
        """
        self.action = action

def get_obs(infoset):
    """
    This function obtains observations with imperfect information
    from the infoset. It has three branches since we encode
    different features for different positions.
    
    This function will return dictionary named `obs`. It contains
    several fields. These fields will be used to train the model.
    One can play with those features to improve the performance.

    `position` is a string that can be landlord/pk_dp/second_hand

    `x_batch` is a batch of features (excluding the hisorical moves).
    It also encodes the action feature

    `z_batch` is a batch of features with hisorical moves only.

    `legal_actions` is the legal moves

    `x_no_action`: the features (exluding the hitorical moves and
    the action features). It does not have the batch dim.

    `z`: same as z_batch but not a batch.
    """
    return _get_obs_landlord(infoset)

def _get_one_hot_array(num_left_cards, max_num_cards): # one_hot for num_left_cards
    """
    A utility function to obtain one-hot endoding
    """
    one_hot = np.zeros(max_num_cards)
    if num_left_cards >= 1:
        one_hot[num_left_cards - 1] = 1
    return one_hot

def _cards2array(list_cards): # size of 42
    """
    A utility function that transforms the actions, i.e.,
    A list of integers into card matrix. Here we remove
    the six entries that are always zero and flatten the
    the representations.
    """
    if len(list_cards) == 0:
        return np.zeros(42, dtype=np.int8) # 21 * 2

    matrix = np.zeros([2, 21], dtype=np.int8)
    counter = Counter(list_cards)
    for card, num_times in counter.items():
        matrix[:, card] = NumOnes2Array[num_times]
    return matrix.flatten('F')

def _action_seq_list2array(action_seq_list):
    """
    A utility function to encode the historical moves.
    We encode the historical 15 actions. If there is
    no 15 actions, we pad the features with 0. Since
    three moves is a round in DouDizhu, we concatenate
    the representations for each consecutive three moves.
    Finally, we obtain a 5x162 matrix, which will be fed
    into LSTM for encoding.
    """
    action_seq_array = np.zeros((len(action_seq_list), 42))
    for row, list_cards in enumerate(action_seq_list):
        action_seq_array[row, :] = _cards2array(list_cards)
    action_seq_array = action_seq_array.reshape(5, 126)
    return action_seq_array

def _process_action_seq(sequence, length=15):
    """
    A utility function encoding historical moves. We
    encode 15 moves. If there is no 15 moves, we pad
    with zeros.
    """
    sequence = sequence[-length:].copy()
    if len(sequence) < length:
        empty_sequence = [[] for _ in range(length - len(sequence))]
        empty_sequence.extend(sequence)
        sequence = empty_sequence
    return sequence

def _get_one_hot_bomb(bomb_num):
    """
    A utility function to encode the number of bombs
    into one-hot representation.
    """
    one_hot = np.zeros(15)
    one_hot[bomb_num] = 1
    return one_hot

def _get_obs_landlord(infoset): # MYWEN obs details
    """
    Obttain the landlord features. See Table 4 in
    https://arxiv.org/pdf/2106.06135.pdf
    """
    num_legal_actions = len(infoset.legal_actions)
    my_handcards = _cards2array(infoset.player_hand_cards)
    my_handcards_batch = np.repeat(my_handcards[np.newaxis, :],
                                   num_legal_actions, axis=0)

    player_deck_cards = _cards2array(infoset.player_deck_cards)
    player_deck_cards_batch = np.repeat(player_deck_cards[np.newaxis, :],
                                      num_legal_actions, axis=0)
    
    last_action = _cards2array(infoset.last_move)
    last_action_batch = np.repeat(last_action[np.newaxis, :],
                                  num_legal_actions, axis=0)
    
    my_handcards_left = _get_one_hot_array(
        len(infoset.player_hand_cards), 10)
    my_handcards_left_batch = np.repeat(
        my_handcards_left[np.newaxis, :],
        num_legal_actions, axis=0)
    
    rivals_left = _get_one_hot_array(
        infoset.rival_num_on_battlefield, 7)
    rivals_left_batch = np.repeat(
        rivals_left[np.newaxis, :],
        num_legal_actions, axis=0)

    # 5 * 7
    companions_batch = np.zeros(rivals_left_batch.shape)
    companions_spell_power_batch = np.zeros(rivals_left_batch.shape)
    companions_spell_burst_batch = np.zeros(rivals_left_batch.shape)
    aoe_spell_batch = np.zeros(rivals_left_batch.shape)
    spell_batch = np.zeros(rivals_left_batch.shape)
    
    advice_batch = np.zeros(my_handcards_left_batch.shape)
    my_action_batch = np.zeros(my_handcards_batch.shape)
    other_details = []
    for j, action in enumerate(infoset.legal_actions):
        card_count_by_type = infoset.card_count_by_type[j]
        companions_batch[j,:] = _get_one_hot_array(infoset.companion_num_on_battlefield + card_count_by_type[CardTypeToIndex["minion"]], 7)
        companions_spell_power_batch[j,:] = _get_one_hot_array(infoset.companion_with_power_inprove + card_count_by_type[CardTypeToIndex["minion_increase_spell_power"]], 7)
        companions_spell_burst_batch[j,:] = _get_one_hot_array(infoset.companion_with_spell_burst + card_count_by_type[CardTypeToIndex["minion_with_burst"]], 7)
        aoe_spell_batch[j,:] = _get_one_hot_array(card_count_by_type[CardTypeToIndex["aoe_spell"]], 7)
        spell_batch[j,:] = _get_one_hot_array(card_count_by_type[CardTypeToIndex["spell"]], 7)
        
        advice_batch[j,:] = _get_one_hot_array(infoset.advice[j], 10)
        
        my_action_batch[j, :] = _cards2array(action)
        
        other_details.append([infoset.rival_num_on_battlefield,
                              infoset.companion_num_on_battlefield + card_count_by_type[CardTypeToIndex["minion"]],
                              infoset.companion_with_power_inprove + card_count_by_type[CardTypeToIndex["minion_increase_spell_power"]],
                              infoset.companion_with_spell_burst + card_count_by_type[CardTypeToIndex["minion_with_burst"]],
                              card_count_by_type[CardTypeToIndex["aoe_spell"]],
                              card_count_by_type[CardTypeToIndex["spell"]],
                              infoset.advice[j]])

    x_batch = np.hstack((my_handcards_batch, # 42
                         player_deck_cards_batch, # 42
                         last_action_batch, # 42
                         my_handcards_left_batch, # 10
                         rivals_left_batch, # 7
                         companions_batch, # 7
                         companions_spell_power_batch, # 7
                         companions_spell_burst_batch, # 7
                         aoe_spell_batch, # 7
                         spell_batch, # 7
                         advice_batch, # 10
                         my_action_batch)) # 42
    x_no_action = np.hstack((my_handcards,
                            player_deck_cards,
                            last_action,
                            my_handcards_left,
                             ))
    z = _action_seq_list2array(_process_action_seq(
        infoset.played_actions))
    z_batch = np.repeat(
        z[np.newaxis, :, :],
        num_legal_actions, axis=0)
    obs = {
            'position': infoset.player_position,
            'x_batch': x_batch.astype(np.float32), # shape (num_legal_actions, 4 * 42 + 6 * 7 + 2 * 10)
            'z_batch': z_batch.astype(np.float32), # shape (num_legal_actions, 5 * 120)
            'legal_actions': infoset.legal_actions, # shape (num_legal_actions, 40)
            'x_no_action': x_no_action.astype(np.int8), # shape (3 * 42 + 1 * 10),
            'other_details': other_details, # shape (num_legal_actions, 6 * 7 + 10)
            'z': z.astype(np.int8),
          }
    return obs
