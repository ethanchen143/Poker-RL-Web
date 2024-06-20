from bots.player import Player
import random

class RandomBot(Player):
    def __init__(self, name, chips):
        super().__init__(name, chips)
        self.initial_chips = chips
    
    def get_action(self, game, current_position, effective_stack):
        legal_actions = self.get_legal_actions(game, effective_stack)   
        action = random.choice(legal_actions)
        return action