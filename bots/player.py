from utils import Card

class Player:
    def __init__(self, name, chips):
        self.name = name
        self.score = 0
        self.chips = chips
        self.initial_chips = 1000
        self.hand = []
        self.current_bet = 0
        self.folded = False
        self.playpot = 0 # decides which pot player is playing for
        self.lose_game = False

    def to_dict(self):
        return {
            'name': self.name,
            'score': self.score,
            'chips': self.chips,
            'hand': [card.to_dict() for card in self.hand], 
            'current_bet': self.current_bet,
            'folded': self.folded,
            'playpot': self.playpot,
            'lose_game':self.lose_game,
        }

    @staticmethod
    def from_dict(d):
        player = Player(d['name'], d['chips'])
        player.score = d['score']
        player.hand = [Card.from_dict(card) for card in d['hand']] 
        player.current_bet = d['current_bet']
        player.folded = d['folded']
        player.playpot = d['playpot']
        player.initial_chips = 1000
        player.lose_game = d['lose_game']
        return player
        
    def place_bet(self, amount):
        if amount > self.chips:
            raise ValueError(f"{self.name} does not have enough chips to bet {amount}")
        self.chips -= amount
        self.current_bet += amount

    def reset_for_round(self):
        self.hand = []
        self.current_bet = 0
        self.folded = False
        self.playpot = 0
        
    def is_valid_raise(self, raise_action, pot, effective_stack, call_amount):
        percentage = int(raise_action.split('_')[1])
        amount = (percentage / 100) * pot
        return amount <= (effective_stack - call_amount)

    def get_legal_actions(self, game, effective_stack):
        legal_actions = []
        game.pot = sum(game.pots)
        call_amount = game.current_bet - self.current_bet

        if self.chips <= 0:
            return ['check']
        
        if self.current_bet < game.current_bet:
            legal_actions.append('fold')
        
        if self.current_bet == game.current_bet:
            legal_actions.append('check')
        else:
            if self.chips > 0:
                legal_actions.append('call')
        
        if self.chips > game.current_bet:
            if game.community_cards:
                # Post-Flop
                pot_fraction_raises = ['raise_50', 'raise_100']
            else:
                # Pre-Flop
                pot_fraction_raises = ['raise_100']

            # Calculate the actual raise amounts and filter out invalid ones
            valid_raises = [
                raise_action for raise_action in pot_fraction_raises
                if self.is_valid_raise(raise_action, game.pot, effective_stack, call_amount)
            ]
            legal_actions.extend(valid_raises)
            legal_actions.append('all_in')

        return legal_actions

    def check_rebuy(self, game):
        if self.chips <= game.big_blind:
            # take chips from the deepest stack            
            game.log_message(f"{self.name} rebuys for {self.initial_chips} chips.")
            self.chips = self.initial_chips
            self.score -= 1
            self.lose_game = True

    def __repr__(self):
        return f"{self.name}: {self.chips} chips"