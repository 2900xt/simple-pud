#pragma once

// Numbers: 23456789TJQKA
// Suit:    HDSC

// format = 2HAC (A2o)

struct poker_game_state {
  int num_players;
  char hands[9][4];
  char community[5][4];
  enum class stage { PREFLOP, FLOP, TURN, RIVER } game_stage;
  enum class position { SB, BB, UTG, UTG1, UTG2, LJ, HJ, CO, BTN } hero_pos;
};