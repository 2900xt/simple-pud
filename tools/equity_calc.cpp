#include "../include/equity.h"
#include <iostream>
#include <sstream>
#include <string>

static void print_usage() {
  std::cout << "Usage: equity_calc <range1> <range2> [board] [simulations]\n"
            << "\n"
            << "Ranges:  AA,KK,AKs,TT+,ATs-A7s,AsKh\n"
            << "Board:   Ah Kd 5c  (space-separated cards)\n"
            << "Sims:    number of Monte Carlo iterations (default: 100000)\n"
            << "\n"
            << "Examples:\n"
            << "  equity_calc \"AA\" \"KK\"\n"
            << "  equity_calc \"AKs\" \"QQ\" \"Ah Kd 5c\"\n"
            << "  equity_calc \"TT+,AKs\" \"88-66,AJs\" \"\" 500000\n";
}

static std::vector<int> parse_board(const std::string &board_str) {
  std::vector<int> board;
  if (board_str.empty()) return board;
  std::stringstream ss(board_str);
  std::string token;
  while (ss >> token) {
    int c = card_from_string(token);
    if (c >= 0) board.push_back(c);
  }
  return board;
}

int main(int argc, char *argv[]) {
  if (argc < 3) {
    print_usage();
    return 1;
  }

  std::string range1_str = argv[1];
  std::string range2_str = argv[2];
  std::string board_str = argc > 3 ? argv[3] : "";
  int num_sims = argc > 4 ? std::stoi(argv[4]) : 100000;

  auto range1 = parse_range(range1_str);
  auto range2 = parse_range(range2_str);
  auto board = parse_board(board_str);

  if (range1.empty()) {
    std::cerr << "Error: Could not parse range 1: " << range1_str << "\n";
    return 1;
  }
  if (range2.empty()) {
    std::cerr << "Error: Could not parse range 2: " << range2_str << "\n";
    return 1;
  }

  const char *stage_names[] = {"Preflop", "Invalid", "Invalid",
                               "Flop",    "Turn",    "River"};
  int board_size = (int)board.size();
  std::string stage =
      (board_size == 0)   ? "Preflop"
      : (board_size == 3) ? "Flop"
      : (board_size == 4) ? "Turn"
      : (board_size == 5) ? "River"
                          : "Unknown";

  std::cout << "Range 1: " << range1_str << " (" << range1.size()
            << " combos)\n";
  std::cout << "Range 2: " << range2_str << " (" << range2.size()
            << " combos)\n";
  std::cout << "Board:   ";
  if (board.empty())
    std::cout << "(none)";
  else
    for (int c : board) std::cout << card_to_string(c) << " ";
  std::cout << "\n";
  std::cout << "Stage:   " << stage << "\n";
  std::cout << "Sims:    " << num_sims << "\n\n";

  auto result = calculate_equity(range1, range2, board, num_sims);

  std::cout << "Results (" << result.num_simulations << " valid sims):\n";
  std::cout << "  Range 1 equity: " << result.equity[0] << "%\n";
  std::cout << "  Range 2 equity: " << result.equity[1] << "%\n";
  std::cout << "  Range 1 wins:   " << result.wins[0] << "%\n";
  std::cout << "  Range 2 wins:   " << result.wins[1] << "%\n";
  std::cout << "  Ties:           " << result.ties << "%\n";

  // JSON output for GUI consumption
  std::cout << "\n---JSON---\n";
  std::cout << "{\"equity1\":" << result.equity[0]
            << ",\"equity2\":" << result.equity[1]
            << ",\"wins1\":" << result.wins[0]
            << ",\"wins2\":" << result.wins[1] << ",\"ties\":" << result.ties
            << ",\"sims\":" << result.num_simulations
            << ",\"combos1\":" << range1.size()
            << ",\"combos2\":" << range2.size() << "}\n";

  return 0;
}
