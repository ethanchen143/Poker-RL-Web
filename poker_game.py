from bots.rl_bot import QLearningBot, Player
from utils import describe_hand, Deck, card_to_tuple, Card
from hand_rank_monte_carlo import get_best_hand

class PokerGame:
    def __init__(self, players=[], big_blind=10, small_blind=5):
        self.players = players
        self.deck = Deck()
        self.community_cards = []
        self.pots = [0, 0, 0, 0, 0, 0]  # One main pot and five side pots maximum.
        self.pot_index = 0
        self.current_bet = 0
        self.big_blind = big_blind
        self.small_blind = small_blind
        self.dealer_position = 0
        self.stage = 'Pre-Flop'
        self.actions = []  # Keep track of action history of a round
        self.log = []  # Log messages
        self.score_log = {player.name: [0] for player in players}
        self.step = 0
        self.starting_chips = {}

        # For Betting
        self.more_action = True
        self.start_position = (self.dealer_position + 3) % len(self.players) if self.stage == 'Pre-Flop' else (self.dealer_position + 1) % len(self.players)
        self.current_position = self.start_position
        self.last_to_act = (self.start_position - 1) % len(self.players)
        self.all_in_action = False
        
        # For Player Acting
        self.player_legal_actions = []
        self.player_action = ''
        self.recommendation = ''
        

    def to_dict(self):
        return {
            'players': [p.to_dict() for p in self.players],
            'deck': self.deck.to_dict(),
            'community_cards': [card.to_dict() for card in self.community_cards],
            'pots': self.pots,
            'pot_index': self.pot_index,
            'current_bet': self.current_bet,
            'big_blind': self.big_blind,
            'small_blind': self.small_blind,
            'dealer_position': self.dealer_position,
            'stage': self.stage,
            'actions': self.actions,
            'score_log': self.score_log,
            'step': self.step,
            'more_action': self.more_action,
            'start_position': self.start_position,
            'current_position': self.current_position,
            'last_to_act': self.last_to_act,
            'all_in_action': self.all_in_action,
            'log': self.log[-10:],
            'starting_chips': self.starting_chips,
            'player_legal_actions': self.player_legal_actions,
            'player_action': self.player_action,
            'recommendation': self.recommendation
        }
        

    @staticmethod
    def from_dict(d,shared_q_table):
        players = [QLearningBot.from_dict(p,shared_q_table) if p['name'][:3]=='Bot' else Player.from_dict(p) for p in d['players']]
        game = PokerGame(players, big_blind=d['big_blind'], small_blind=d['small_blind'])
        game.deck = Deck.from_dict(d['deck'])
        game.community_cards = [Card.from_dict(card) for card in d['community_cards']]
        game.pots = d['pots']
        game.pot_index = d['pot_index']
        game.current_bet = d['current_bet']
        game.dealer_position = d['dealer_position']
        game.stage = d['stage']
        game.actions = d['actions']
        game.score_log = d['score_log']
        game.step = d['step']
        game.more_action = d['more_action']
        game.start_position = d['start_position']
        game.current_position = d['current_position']
        game.last_to_act = d['last_to_act']
        game.all_in_action = d['all_in_action']
        game.log = d['log']
        game.starting_chips = d['starting_chips']
        game.player_legal_actions = d['player_legal_actions']
        game.player_action = d['player_action']
        game.recommendation = d['recommendation']
        return game
    

    def log_message(self, message):
        self.log.append(message)
        # print(message)

    def rotate_dealer(self):
        self.dealer_position = (self.dealer_position + 1) % len(self.players)

    def deal_hands(self):
        self.deck.reset()
        for player in self.players:
            player.hand = [self.deck.deal(), self.deck.deal()]

    def post_blinds(self):
        small_blind_position = (self.dealer_position + 1) % len(self.players)
        big_blind_position = (self.dealer_position + 2) % len(self.players)
        self.players[small_blind_position].place_bet(self.small_blind)
        self.players[big_blind_position].place_bet(self.big_blind)
        self.pots[0] += self.small_blind + self.big_blind
        self.current_bet = self.big_blind
        self.log_message(f"{self.players[small_blind_position].name} posts small blind ({self.small_blind})")
        self.log_message(f"{self.players[big_blind_position].name} posts big blind ({self.big_blind})")
    
    def log_action(self, player_index, action):
        position = self.get_player_position(player_index)
        self.actions.append(position)
        self.actions.append(action)
        
    def get_player_position(self, player_index):
        position = (player_index - self.dealer_position) % len(self.players)
        position_names = ['btn', 'sb', 'bb', 'utg', 'mp', 'co']
        return position_names[position] if position < len(position_names) else f'pos_{position}'            

    def call_bet(self, player):
        if player.chips < self.current_bet - player.current_bet:
            all_in_amount = player.chips
            player.place_bet(all_in_amount)
            actual_call_amount = player.current_bet
            for p in self.players:
                if not p.folded and p != player:
                    if p.current_bet > actual_call_amount:
                        excess_amount = p.current_bet - actual_call_amount
                        self.pots[self.pot_index] -= excess_amount
                        p.chips += excess_amount
                        p.current_bet = actual_call_amount
            self.current_bet = actual_call_amount
            self.pots[self.pot_index] += actual_call_amount
        else:
            call_amount = self.current_bet - player.current_bet
            player.place_bet(call_amount)
            self.pots[self.pot_index] += call_amount
            
    def raise_bet(self, player, amount):
        player.place_bet(amount)
        self.current_bet += amount
        self.pots[self.pot_index] += amount

    def deal_flop(self):
        self.community_cards = [self.deck.deal() for _ in range(3)]

    def deal_turn_or_river(self):
        self.community_cards.append(self.deck.deal())

    def determine_winner(self):
        for i in range(len(self.pots)):
            if self.pots[i] == 0:
                continue
            entitled_players = [p for p in self.players if not p.folded and p.playpot >= i]
            if len(entitled_players) == 1:
                winner = entitled_players[0]
                winner.chips += self.pots[i]
                self.log_message(f"{winner.name} wins {self.pots[i]} chips")
                self.pots[i] = 0
                continue
            best_hands = []
            for player in entitled_players:
                best_hand = get_best_hand([card_to_tuple(card) for card in player.hand], [card_to_tuple(card) for card in self.community_cards])
                best_hands.append((player, best_hand))
            if not best_hands: # safeguarding
                self.log_message('Something went wrong, no winner.')
                return
            best_hands.sort(key=lambda x: x[1], reverse=True)
            best_hand_rank = best_hands[0][1]
            winners = [p for p, hand in best_hands if hand == best_hand_rank]
            split_pot = self.pots[i] // len(winners)
            for winner in winners:
                winner.chips += split_pot
                self.log_message(f"{winner.name} wins {split_pot} chips with hand: {describe_hand(best_hand_rank)}")
            self.pots[i] = 0
            
        for player in self.players:
            if isinstance(player, QLearningBot):
                reward = player.chips - self.starting_chips[player.name]
                player.receive_reward(reward)

    def reset_for_new_round(self):
        for p in self.players:
            p.check_rebuy(self)
        self.starting_chips = {p.name: p.chips for p in self.players}
        self.community_cards = []
        self.pots = [0,0,0,0,0,0]
        self.current_bet = 0
        self.pot_index = 0
        self.actions = []
        self.stage = 'Pre-Flop'
        
        self.more_action = True
        self.start_position = (self.dealer_position + 3) % len(self.players) if self.stage == 'Pre-Flop' else (self.dealer_position + 1) % len(self.players)
        self.current_position = self.start_position
        self.last_to_act = (self.start_position - 1) % len(self.players)
        self.all_in_action = False
        
        self.player_legal_actions = []
        self.player_action = ''
        self.recommendation = ''

        for player in self.players:
            player.reset_for_round()