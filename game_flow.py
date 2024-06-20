from poker_game import PokerGame
from bots.player import Player
from bots.rl_bot import QLearningBot
import sys
import json
import os

Q_TABLE = {}

def load_q_table():
    global Q_TABLE
    q_table_filename = "./outputs/q_table.json"
    with open(q_table_filename, 'r') as q_table_file:
        Q_TABLE = json.load(q_table_file)
        Q_TABLE = {eval(k): v for k, v in Q_TABLE.items()}
        print(f"Q-table loaded, length: {len(Q_TABLE)}")

load_q_table()

def setup():
    global Q_TABLE
    load_q_table()  # Load Q-table once
    ricky = QLearningBot(name="Bot_Ricky", chips=1000, shared_q_table=Q_TABLE)
    julian = QLearningBot(name="Bot_Julian", chips=1000, shared_q_table=Q_TABLE)
    player = Player(name="You", chips=1000)
    players = [player, ricky, julian]
    game = PokerGame(players)
    save_game(game)
    return game

def save_game(game):
    temp_path = 'game_state_temp.json'
    final_path = 'game_state.json'
    with open(temp_path, 'w') as file:
        json.dump(game.to_dict(), file)
    os.replace(temp_path, final_path)

def load_game():
    with open('game_state.json', 'r') as file:
        game_state = json.load(file)
        game = PokerGame.from_dict(game_state, Q_TABLE)
        return game

def bet_game(game):
    player = game.players[game.current_position]
    if not player.folded and player.chips > 0:
        try:
            max_opponent_stack = max(p.chips for p in game.players if p != player and p.chips > 0 and not p.folded)
        except ValueError:
            max_opponent_stack = 0
        effective_stack = min(player.chips, max_opponent_stack) # calculating effective stack for raising
        if isinstance(player, QLearningBot):
            action = player.get_action(game, game.current_position, effective_stack)
        else:
            if not game.player_legal_actions: # if needs player action, send back legal actions
                game.player_legal_actions = player.get_legal_actions(game,effective_stack)
                save_game(game)
                return
            else:
                game.player_legal_actions = []
                action = game.player_action
                game.player_action = ''
        if game.all_in_action:
            action = 'call' if 'fold' not in action else 'fold'
        if action == 'fold':
            player.folded = True
            game.log_message(f"{player.name} folds")
        elif action == 'call':
            game.call_bet(player)
            game.log_message(f"{player.name} calls")
        elif action == 'check':
            game.log_message(f"{player.name} checks")
        elif action == 'all_in':
            game.call_bet(player)
            effective_stack = min(player.chips, max_opponent_stack)
            game.raise_bet(player, effective_stack)
            game.all_in_action = True
            game.last_to_act = (game.current_position - 1) % len(game.players)
            game.log_message(f"{player.name} goes all-in")
        elif action.startswith('raise_'):
            percentage = int(action.split('_')[1])
            amount = int((percentage / 100) * sum(game.pots))
            game.call_bet(player)
            game.raise_bet(player, amount)
            game.last_to_act = (game.current_position - 1) % len(game.players)
            game.log_message(f"{player.name} raises {amount}")
        else:
            game.log_message('Something went wrong, no action available.')
        game.log_action(game.current_position, action)
        
    if game.current_position == game.last_to_act:
        if all(p.current_bet == game.current_bet or p.chips == 0 or p.folded for p in game.players):
            if not (game.stage == 'Pre-Flop' and game.get_player_position(game.current_position) == 'sb' and game.actions.count('bb') < 1):
                game.more_action = False
        
    game.current_position = (game.current_position + 1) % len(game.players)
    save_game(game)

import time

def progress_game():
    game = load_game()
    if len(game.player_legal_actions) > 0 and not game.player_action:
        return game
    
    if game.step == 0:
        game.reset_for_new_round()
        game.deal_hands()
        game.post_blinds()
        game.step += 1
        save_game(game)
        # time.sleep(2) # sleep 2 seconds when round starts
        return game
    
    def handle_bet_round_end():
        fold_count = 0
        all_count = 0
        for player in game.players:
            player.current_bet = 0 # clear out current bet
            if player.folded:
                fold_count += 1
            if player.chips == 0:
                all_count += 1
        if fold_count+all_count >= 2: # if both folded/all in, skip next betting round
            game.more_action = False
        
        if fold_count >= 2:
            game.step = 5
        
            
        game.current_bet = 0
        game.actions = [] # clear out actions for next round
        game.log = []
        game.player_action = ''
        game.start_position = (game.dealer_position + 3) % len(game.players) if game.stage == 'Pre-Flop' else (game.dealer_position + 1) % len(game.players)
        game.current_position = game.start_position
        game.last_to_act = (game.start_position - 1) % len(game.players)
        if game.all_in_action: # if all in, devide pots
            game.pot_index += 1
            for p in game.players:
                if not p.folded and p.chips > 0:
                    p.playpot = game.pot_index
        
    if game.step == 1:
        if game.more_action: # pre flop betting
            bet_game(game)
            save_game(game)
            return game
        game.deal_flop()
        game.step += 1
        game.more_action = True
        game.stage = 'Flop'
        handle_bet_round_end()
        save_game(game)
        return game

    if game.step == 2: # flop betting round
        if game.more_action:
            bet_game(game)
            save_game(game)
            return game
        game.deal_turn_or_river()
        game.step += 1
        game.more_action = True
        game.stage = 'Turn'
        handle_bet_round_end()
        save_game(game)
        return game
    
    if game.step == 3: # turn betting round
        if game.more_action:
            bet_game(game)
            save_game(game)
            return game
        game.deal_turn_or_river()
        game.step += 1
        game.more_action = True
        game.stage = 'River'
        handle_bet_round_end()
        save_game(game)
        return game

    if game.step == 4: # river betting round
        if game.more_action:
            bet_game(game)
            save_game(game)
            return game
        game.step += 1
        handle_bet_round_end()
        save_game(game)
        return game
     
    if game.step == 5: # ends
        game.determine_winner()
        game.step += 1
        save_game(game)
        return game
    
    if game.step == 6: 
        time.sleep(1) # show result page for 1 sec
        game.step = 0
        game.rotate_dealer()
        save_game(game)
        return game

from utils import evaluate_hand_strength
def get_rec():
    game = load_game()
    position = game.get_player_position(0)
    hand_strength = evaluate_hand_strength(game, game.players[0], 200)
    past_actions = game.actions
    pot_stack_ratio = min(10,round(game.pots[0] * 10 / game.players[0].chips))
    key = (
        game.stage,
        position,
        pot_stack_ratio,
        hand_strength,
        tuple(past_actions),
    )
    q_values = [round(Q_TABLE.get((key, action), 0)) for action in game.player_legal_actions]
    recommendation = f'Strength ({hand_strength * 5}) \n'
    for i in range(len(game.player_legal_actions)):
        recommendation += f'{game.player_legal_actions[i]}: {q_values[i]} \n'
    game.recommendation = recommendation
    save_game(game)
    return game


while True:
    action = input().strip()
    if action == 'setup':
        game = setup()
    elif action == 'progress':
        game = progress_game()
    elif action == 'rec':
        game = get_rec()
    else:
        game = load_game()
        game.player_action = action[7:]  # Extract action after 'action_'
        bet_game(game)
        save_game(game)
    
    # Send the updated game state to Node.js
    with open('game_state.json', 'r') as file:
        game_state = file.read()
        print(game_state)
        sys.stdout.flush()