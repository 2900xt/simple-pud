#pragma once

// Numbers: 23456789TJQKA
// Suit:    HDSC

// format = 2HAC (A2o)

typedef char card[3];

struct poker_game_state {
  int num_players;
  card hands[9][2];
  card community[5];
  enum class stage { PREFLOP, FLOP, TURN, RIVER } game_stage;
  enum class position { SB, BB, UTG, UTG1, UTG2, LJ, HJ, CO, BTN } hero_pos;

  card deck[52];
  int next_card = 0;
};

void initialize_solver();
void initialize_game(poker_game_state *game);
