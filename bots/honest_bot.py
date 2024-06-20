from bots.player import Player
from utils import evaluate_hand_strength

class HonestBot(Player):
    def __init__(self, name, chips):
        super().__init__(name, chips)
        self.initial_chips = chips

    def get_action(self, game, current_position, effective_stack):
        legal_actions = self.get_legal_actions(game, effective_stack)
        hand_strength = evaluate_hand_strength(game,self,50) #get rough evaluation
        
        game.log_message(f'hand_strength: {hand_strength}')        
        game.log_message(f'legal_actions: {legal_actions}')
        
        raise_count = game.actions.count('raise_50') +  game.actions.count('raise_100')
        
        if 'check' in legal_actions and hand_strength < 10:
            return 'check' #check 50% of the hands
        
        if 'all_in' in game.actions:
            if hand_strength >= 18:
                return 'call'
            return 'fold'
        
        if game.stage == 'Pre-Flop' and hand_strength < 10:
            return 'fold' #fold 50% of the hands preflop
        
        if raise_count == 1:
            if hand_strength <= 10:
                return 'fold'
            if hand_strength <= 15:
                return 'call'
            
        if raise_count == 2:
            if hand_strength <= 15:
                return 'fold'
            if hand_strength <= 18:
                return 'call'

        if raise_count == 3:
            if hand_strength <= 18:
                return 'fold'
        
        # if not enough raise, dont go all in
        if 'raise_100' in legal_actions and raise_count <= 3:
            legal_actions = legal_actions[:-1]
        
        index = round((hand_strength / 20) * (len(legal_actions) - 1))        
        action = legal_actions[index]
        
        return action