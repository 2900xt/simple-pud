#pragma once

// Numbers: 23456789TJQKA
// Suit:    HDSC

// format = 2HAC (A2o)

typedef char card[3];

struct poker_game_state {
  int num_players;
  card hands[9][2];
  card community[5];
  enum class stage { PREFLOP, FLOP, TURN, RIVER, SHOWDOWN } game_stage;
  enum class position { SB, BB, UTG, UTG1, UTG2, LJ, HJ, CO, BTN } hero_pos;

  // Betting and Stacks
  int stacks[9];
  int bets[9];
  bool folded[9];
  int pot;
  int current_bet;
  int small_blind;
  int big_blind;
  int dealer_pos;
  int current_player;

  card deck[52];
  int next_card = 0;
};

void initialize_solver();
void initialize_game(poker_game_state *game);
void play_game(poker_game_state *game);
void evaluate_winner(poker_game_state *game);
