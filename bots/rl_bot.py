import random
from utils import evaluate_hand_strength, Card
from bots.player import Player
import json

class QLearningBot(Player):
    def __init__(self, name, chips, shared_q_table = None):
        super().__init__(name, chips)
        self.q_table = shared_q_table if shared_q_table is not None else {}
        self.alpha = 1 #learning rate
        self.epsilon = 0.1 #exploration rate
        self.states_actions = []

    def to_dict(self):
        base_dict = super().to_dict()
        base_dict.update({
            'states_actions': self.states_actions,
        })
        return base_dict

    @staticmethod
    def from_dict(d,shared_q_table):
        player = Player.from_dict(d)
        bot = QLearningBot(
            player.name,
            player.chips,
            shared_q_table,
        )
        # additional player atributes
        bot.score = player.score
        bot.hand = player.hand
        bot.current_bet = player.current_bet
        bot.folded = player.folded
        bot.playpot = player.playpot
        bot.states_actions = d.get('states_actions', [])
        return bot

    def get_state(self, game, current_position):
        """ Convert the game state to a tuple that can be used as a dictionary key. """
        position = game.get_player_position(current_position)
        hand_strength = 0
        for pair in self.states_actions:
            if pair[0][0] == game.stage:
                hand_strength = pair[0][2]
        if hand_strength == 0:
            hand_strength = evaluate_hand_strength(game,self,200)
        past_actions = game.actions
        return (
            game.stage,
            position,
            hand_strength,
            tuple(past_actions),
        )
        
    def choose_action(self, state, legal_actions, game):
        """ Choose an action based on the Q-Table, with exploration. """
        if random.random() < self.epsilon:
            return random.choice(legal_actions)  # Explore
        else:
            q_values = [self.q_table.get((state, action), 0) for action in legal_actions]
            max_q = max(q_values)
            return legal_actions[q_values.index(max_q)]  # Exploit

    def get_action(self, game, current_position, effective_stack):
        state = self.get_state(game, current_position)
        legal_actions = self.get_legal_actions(game, effective_stack)
        action = self.choose_action(state, legal_actions, game)
        self.states_actions.append((state,action))
        return action

    def convert_lists_to_tuples(self,data):
        if isinstance(data, list):
            return tuple(self.convert_lists_to_tuples(item) for item in data)
        elif isinstance(data, dict):
            return {key: self.convert_lists_to_tuples(value) for key, value in data.items()}
        else:
            return data
        
    def receive_reward(self, reward):
        for state, action in self.states_actions:
            state_key = repr(self.convert_lists_to_tuples(state))
            action_key = repr(self.convert_lists_to_tuples(action))
            q_table_key = f"({state_key}, {action_key})"
            q_table_key = eval(q_table_key)
            old_q_value = self.q_table.get(q_table_key, 0)
            new_q_value = old_q_value + self.alpha * reward
            self.q_table[q_table_key] = new_q_value
        
        q_table_filename = "./outputs/q_table.json"
        with open(q_table_filename, 'w') as q_table_file:
            json.dump({str(k): v for k, v in self.q_table.items()}, q_table_file, indent=2)
        
        self.states_actions = []