#include "../include/equity.h"
#include <algorithm>
#include <random>
#include <sstream>
#include <cstring>

// ─── Card utilities ─────────────────────────────────────────────────────────

int eq_parse_rank(char c) {
  if (c >= '2' && c <= '9') return c - '2';
  if (c == 'T' || c == 't') return 8;
  if (c == 'J' || c == 'j') return 9;
  if (c == 'Q' || c == 'q') return 10;
  if (c == 'K' || c == 'k') return 11;
  if (c == 'A' || c == 'a') return 12;
  return -1;
}

int eq_parse_suit(char c) {
  if (c == 'h' || c == 'H') return 0;
  if (c == 'd' || c == 'D') return 1;
  if (c == 's' || c == 'S') return 2;
  if (c == 'c' || c == 'C') return 3;
  return -1;
}

char rank_to_char(int r) {
  const char *ranks = "23456789TJQKA";
  if (r < 0 || r > 12) return '?';
  return ranks[r];
}

char suit_to_char(int s) {
  const char *suits = "hdsc";
  if (s < 0 || s > 3) return '?';
  return suits[s];
}

int card_from_string(const std::string &s) {
  if (s.size() < 2) return -1;
  int r = eq_parse_rank(s[0]);
  int su = eq_parse_suit(s[1]);
  if (r < 0 || su < 0) return -1;
  return r * 4 + su;
}

std::string card_to_string(int idx) {
  if (idx < 0 || idx > 51) return "??";
  std::string s;
  s += rank_to_char(idx / 4);
  s += suit_to_char(idx % 4);
  return s;
}

// ─── Hand evaluation ────────────────────────────────────────────────────────

long long evaluate_5(const int r[5], const int s[5]) {
  std::pair<int, int> cards[5];
  for (int i = 0; i < 5; ++i)
    cards[i] = {r[i], s[i]};
  std::sort(cards, cards + 5,
            [](auto a, auto b) { return a.first > b.first; });

  bool flush = true;
  for (int i = 1; i < 5; ++i)
    if (cards[i].second != cards[0].second) flush = false;

  bool straight = true;
  for (int i = 0; i < 4; ++i)
    if (cards[i].first != cards[i + 1].first + 1) straight = false;

  // Ace-low straight: A5432
  bool ace_low = false;
  if (!straight && cards[0].first == 12 && cards[1].first == 3 &&
      cards[2].first == 2 && cards[3].first == 1 && cards[4].first == 0) {
    straight = true;
    ace_low = true;
  }

  if (straight && flush)
    return (8LL << 20) | (ace_low ? 3 : cards[0].first);

  int counts[13] = {};
  for (int i = 0; i < 5; ++i) counts[cards[i].first]++;

  int quads = -1, trips = -1, pair1 = -1, pair2 = -1;
  for (int i = 12; i >= 0; --i) {
    if (counts[i] == 4) quads = i;
    else if (counts[i] == 3) trips = i;
    else if (counts[i] == 2) {
      if (pair1 == -1) pair1 = i;
      else pair2 = i;
    }
  }

  if (quads != -1) {
    int k = -1;
    for (int i = 0; i < 5; ++i)
      if (cards[i].first != quads) k = cards[i].first;
    return (7LL << 20) | (quads << 16) | (k << 12);
  }

  if (trips != -1 && pair1 != -1)
    return (6LL << 20) | (trips << 16) | (pair1 << 12);

  if (flush)
    return (5LL << 20) | (cards[0].first << 16) | (cards[1].first << 12) |
           (cards[2].first << 8) | (cards[3].first << 4) | cards[4].first;

  if (straight)
    return (4LL << 20) | (ace_low ? 3 : cards[0].first);

  if (trips != -1) {
    int k1 = -1, k2 = -1;
    for (int i = 0; i < 5; ++i) {
      if (cards[i].first != trips) {
        if (k1 == -1) k1 = cards[i].first;
        else k2 = cards[i].first;
      }
    }
    return (3LL << 20) | (trips << 16) | (k1 << 12) | (k2 << 8);
  }

  if (pair1 != -1 && pair2 != -1) {
    int k = -1;
    for (int i = 0; i < 5; ++i)
      if (cards[i].first != pair1 && cards[i].first != pair2)
        k = cards[i].first;
    return (2LL << 20) | (pair1 << 16) | (pair2 << 12) | (k << 8);
  }

  if (pair1 != -1) {
    int k1 = -1, k2 = -1, k3 = -1;
    for (int i = 0; i < 5; ++i) {
      if (cards[i].first != pair1) {
        if (k1 == -1) k1 = cards[i].first;
        else if (k2 == -1) k2 = cards[i].first;
        else k3 = cards[i].first;
      }
    }
    return (1LL << 20) | (pair1 << 16) | (k1 << 12) | (k2 << 8) | (k3 << 4);
  }

  return (long long)cards[0].first << 16 | (cards[1].first << 12) |
         (cards[2].first << 8) | (cards[3].first << 4) | cards[4].first;
}

long long best_hand_7(int ranks[7], int suits[7]) {
  long long best = -1;
  for (int i = 0; i < 7; ++i) {
    for (int j = i + 1; j < 7; ++j) {
      int r[5], s[5];
      int idx = 0;
      for (int k = 0; k < 7; ++k) {
        if (k == i || k == j) continue;
        r[idx] = ranks[k];
        s[idx] = suits[k];
        idx++;
      }
      long long score = evaluate_5(r, s);
      if (score > best) best = score;
    }
  }
  return best;
}

// ─── Range parsing ──────────────────────────────────────────────────────────

static void add_pair_combos(int rank, std::vector<std::array<int, 2>> &out) {
  for (int s1 = 0; s1 < 4; ++s1)
    for (int s2 = s1 + 1; s2 < 4; ++s2)
      out.push_back({rank * 4 + s1, rank * 4 + s2});
}

static void add_suited_combos(int r1, int r2,
                               std::vector<std::array<int, 2>> &out) {
  for (int s = 0; s < 4; ++s)
    out.push_back({r1 * 4 + s, r2 * 4 + s});
}

static void add_offsuit_combos(int r1, int r2,
                                std::vector<std::array<int, 2>> &out) {
  for (int s1 = 0; s1 < 4; ++s1)
    for (int s2 = 0; s2 < 4; ++s2)
      if (s1 != s2) out.push_back({r1 * 4 + s1, r2 * 4 + s2});
}

static void parse_single_hand(const std::string &token,
                               std::vector<std::array<int, 2>> &out) {
  if (token.empty()) return;

  // Specific combo: "AsKh" (4 chars)
  if (token.size() == 4) {
    int c1 = card_from_string(token.substr(0, 2));
    int c2 = card_from_string(token.substr(2, 2));
    if (c1 >= 0 && c2 >= 0) {
      out.push_back({c1, c2});
      return;
    }
  }

  // Must be at least 2 chars for rank-rank
  if (token.size() < 2) return;

  int r1 = eq_parse_rank(token[0]);
  int r2 = eq_parse_rank(token[1]);
  if (r1 < 0 || r2 < 0) return;

  bool has_suit_qualifier =
      token.size() >= 3 && (token[2] == 's' || token[2] == 'o');
  bool is_suited = has_suit_qualifier && token[2] == 's';
  bool is_offsuit = has_suit_qualifier && token[2] == 'o';
  bool has_plus =
      token.back() == '+' && (token.size() == 3 || token.size() == 4);

  // Ensure r1 >= r2 for non-pair hands
  if (r1 < r2) std::swap(r1, r2);

  if (r1 == r2) {
    // Pair: "AA", "TT+"
    if (has_plus) {
      for (int r = r1; r <= 12; ++r) add_pair_combos(r, out);
    } else {
      add_pair_combos(r1, out);
    }
  } else if (is_suited) {
    if (has_plus) {
      // "ATs+" means ATs, AJs, AQs, AKs (increment lower rank up to r1-1)
      for (int r = r2; r < r1; ++r) add_suited_combos(r1, r, out);
    } else {
      add_suited_combos(r1, r2, out);
    }
  } else if (is_offsuit) {
    if (has_plus) {
      for (int r = r2; r < r1; ++r) add_offsuit_combos(r1, r, out);
    } else {
      add_offsuit_combos(r1, r2, out);
    }
  } else {
    // No suit qualifier: "AK" means both suited and offsuit
    if (has_plus) {
      for (int r = r2; r < r1; ++r) {
        add_suited_combos(r1, r, out);
        add_offsuit_combos(r1, r, out);
      }
    } else {
      add_suited_combos(r1, r2, out);
      add_offsuit_combos(r1, r2, out);
    }
  }
}

// Handle dash ranges like "AA-TT" or "ATs-A7s"
static void parse_dash_range(const std::string &token,
                              std::vector<std::array<int, 2>> &out) {
  size_t dash = token.find('-');
  if (dash == std::string::npos) {
    parse_single_hand(token, out);
    return;
  }

  std::string left = token.substr(0, dash);
  std::string right = token.substr(dash + 1);

  if (left.size() < 2 || right.size() < 2) return;

  int lr1 = eq_parse_rank(left[0]), lr2 = eq_parse_rank(left[1]);
  int rr1 = eq_parse_rank(right[0]), rr2 = eq_parse_rank(right[1]);
  if (lr1 < 0 || lr2 < 0 || rr1 < 0 || rr2 < 0) return;

  if (lr1 < lr2) std::swap(lr1, lr2);
  if (rr1 < rr2) std::swap(rr1, rr2);

  bool l_suited = left.size() >= 3 && left[2] == 's';
  bool l_offsuit = left.size() >= 3 && left[2] == 'o';

  if (lr1 == lr2 && rr1 == rr2) {
    // Pair range: "AA-TT"
    int lo = std::min(lr1, rr1), hi = std::max(lr1, rr1);
    for (int r = lo; r <= hi; ++r) add_pair_combos(r, out);
  } else if (lr1 == rr1) {
    // Same high card: "ATs-A7s"
    int lo = std::min(lr2, rr2), hi = std::max(lr2, rr2);
    for (int r = lo; r <= hi; ++r) {
      if (l_suited)
        add_suited_combos(lr1, r, out);
      else if (l_offsuit)
        add_offsuit_combos(lr1, r, out);
      else {
        add_suited_combos(lr1, r, out);
        add_offsuit_combos(lr1, r, out);
      }
    }
  }
}

std::vector<std::array<int, 2>> parse_range(const std::string &range_str) {
  std::vector<std::array<int, 2>> result;
  std::stringstream ss(range_str);
  std::string token;
  while (std::getline(ss, token, ',')) {
    // Trim whitespace
    size_t start = token.find_first_not_of(" \t");
    size_t end = token.find_last_not_of(" \t");
    if (start == std::string::npos) continue;
    token = token.substr(start, end - start + 1);

    if (token.find('-') != std::string::npos && token.size() > 3)
      parse_dash_range(token, result);
    else
      parse_single_hand(token, result);
  }
  return result;
}

// ─── Monte Carlo equity ─────────────────────────────────────────────────────

EquityResult calculate_equity(const std::vector<std::array<int, 2>> &range1,
                              const std::vector<std::array<int, 2>> &range2,
                              const std::vector<int> &board,
                              int num_simulations) {
  EquityResult result = {};
  if (range1.empty() || range2.empty()) return result;

  std::mt19937 rng(std::random_device{}());

  // Build set of board cards for quick lookup
  bool board_used[52] = {};
  for (int c : board) board_used[c] = true;

  // Pre-filter ranges to remove combos that conflict with the board
  std::vector<std::array<int, 2>> r1_valid, r2_valid;
  for (auto &h : range1)
    if (!board_used[h[0]] && !board_used[h[1]] && h[0] != h[1])
      r1_valid.push_back(h);
  for (auto &h : range2)
    if (!board_used[h[0]] && !board_used[h[1]] && h[0] != h[1])
      r2_valid.push_back(h);

  if (r1_valid.empty() || r2_valid.empty()) return result;

  int cards_to_deal = 5 - (int)board.size();
  int wins1 = 0, wins2 = 0, ties = 0;
  int valid_sims = 0;

  std::uniform_int_distribution<int> dist1(0, (int)r1_valid.size() - 1);
  std::uniform_int_distribution<int> dist2(0, (int)r2_valid.size() - 1);

  for (int sim = 0; sim < num_simulations; ++sim) {
    // Pick random hands from each range
    auto &h1 = r1_valid[dist1(rng)];
    auto &h2 = r2_valid[dist2(rng)];

    // Check for card conflicts between hands
    if (h1[0] == h2[0] || h1[0] == h2[1] || h1[1] == h2[0] ||
        h1[1] == h2[1])
      continue;

    // Build remaining deck
    bool used[52] = {};
    used[h1[0]] = used[h1[1]] = used[h2[0]] = used[h2[1]] = true;
    for (int c : board) used[c] = true;

    int remaining[52];
    int rem_count = 0;
    for (int i = 0; i < 52; ++i)
      if (!used[i]) remaining[rem_count++] = i;

    // Fisher-Yates partial shuffle for the cards we need
    for (int i = 0; i < cards_to_deal && i < rem_count; ++i) {
      std::uniform_int_distribution<int> pick(i, rem_count - 1);
      std::swap(remaining[i], remaining[pick(rng)]);
    }

    // Build full 7-card hands
    int ranks1[7], suits1[7], ranks2[7], suits2[7];
    ranks1[0] = h1[0] / 4; suits1[0] = h1[0] % 4;
    ranks1[1] = h1[1] / 4; suits1[1] = h1[1] % 4;
    ranks2[0] = h2[0] / 4; suits2[0] = h2[0] % 4;
    ranks2[1] = h2[1] / 4; suits2[1] = h2[1] % 4;

    for (int i = 0; i < (int)board.size(); ++i) {
      ranks1[2 + i] = board[i] / 4; suits1[2 + i] = board[i] % 4;
      ranks2[2 + i] = board[i] / 4; suits2[2 + i] = board[i] % 4;
    }
    for (int i = 0; i < cards_to_deal; ++i) {
      int c = remaining[i];
      ranks1[2 + (int)board.size() + i] = c / 4;
      suits1[2 + (int)board.size() + i] = c % 4;
      ranks2[2 + (int)board.size() + i] = c / 4;
      suits2[2 + (int)board.size() + i] = c % 4;
    }

    long long score1 = best_hand_7(ranks1, suits1);
    long long score2 = best_hand_7(ranks2, suits2);

    if (score1 > score2) wins1++;
    else if (score2 > score1) wins2++;
    else ties++;

    valid_sims++;
  }

  if (valid_sims > 0) {
    result.wins[0] = 100.0 * wins1 / valid_sims;
    result.wins[1] = 100.0 * wins2 / valid_sims;
    result.ties = 100.0 * ties / valid_sims;
    result.equity[0] = result.wins[0] + result.ties / 2.0;
    result.equity[1] = result.wins[1] + result.ties / 2.0;
  }
  result.num_simulations = valid_sims;
  return result;
}
