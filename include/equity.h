#pragma once

#include <array>
#include <string>
#include <vector>

// Card index: rank * 4 + suit
// Rank: 0=2, 1=3, ..., 8=T, 9=J, 10=Q, 11=K, 12=A
// Suit: 0=h, 1=d, 2=s, 3=c

struct EquityResult {
  double equity[2];
  double wins[2];
  double ties;
  int num_simulations;
};

int card_from_string(const std::string &s);
std::string card_to_string(int idx);

int eq_parse_rank(char c);
int eq_parse_suit(char c);
char rank_to_char(int r);
char suit_to_char(int s);

long long evaluate_5(const int r[5], const int s[5]);
long long best_hand_7(int ranks[7], int suits[7]);

// Parse a range string like "AA,AKs,TT+" into specific card pairs
// Each pair is {card_index_1, card_index_2}
std::vector<std::array<int, 2>> parse_range(const std::string &range_str);

// Monte Carlo equity calculation
// board: card indices of known community cards (0-5 cards)
EquityResult calculate_equity(const std::vector<std::array<int, 2>> &range1,
                              const std::vector<std::array<int, 2>> &range2,
                              const std::vector<int> &board,
                              int num_simulations = 100000);
