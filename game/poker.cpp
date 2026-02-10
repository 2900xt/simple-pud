#include "../include/poker.h"
#include <bits/stdc++.h>

static card static_deck[52];

static void debug_print_deck(card deck[], int size) {
  for (int i = 0; i < size; i++) {
    std::cout << deck[i] << " ";
  }
  std::cout << std::endl;
}

void initialize_solver() {
  int ptr = 0;
  // Initialize Deck
  for (int card = 1; card <= 13; card++) {
    char card_letter;
    switch (card) {
    case 1:
      card_letter = 'A';
      break;
    case 10:
      card_letter = 'T';
      break;
    case 11:
      card_letter = 'J';
      break;
    case 12:
      card_letter = 'Q';
      break;
    case 13:
      card_letter = 'K';
      break;
    default:
      card_letter = '0' + card;
    }
    char suits[5] = "HDSC";
    for (int suit = 0; suit < 4; suit++) {
      static_deck[ptr][0] = card_letter;
      static_deck[ptr][1] = suits[suit];
      static_deck[ptr][2] = '\0';
      ptr++;
    }
  }
  // debug_print_deck(static_deck, 52);
}

void initialize_game(poker_game_state *game) {
  game->num_players = 9;
  game->small_blind = 1;
  game->big_blind = 2;
  game->pot = 0;
  game->dealer_pos = 0;
  game->game_stage = poker_game_state::stage::PREFLOP;
  game->hero_pos = poker_game_state::position::UTG1; // 3

  // Initialize stacks and players
  for (int i = 0; i < game->num_players; i++) {
    game->stacks[i] = 200;
    game->bets[i] = 0;
    game->folded[i] = false;
  }

  // shuffle deck
  unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
  std::mt19937 rng(seed);

  memcpy(game->deck, static_deck, sizeof(game->deck));
  std::shuffle(game->deck, game->deck + 52, rng);

  std::cout << "Deck Shuffled." << std::endl;
  // debug_print_deck(game->deck, 52);

  // deal hands
  for (int i = 0; i < game->num_players; i++) {
    memcpy(game->hands[i][0], game->deck[game->next_card], sizeof(card));
    game->next_card++;
  }

  for (int i = 0; i < game->num_players; i++) {
    memcpy(game->hands[i][1], game->deck[game->next_card], sizeof(card));
    game->next_card++;
  }
}

void deal_flop(poker_game_state *game) {
  game->game_stage = poker_game_state::stage::FLOP;
  // burn one card
  game->next_card++;

  memcpy(game->community[0], game->deck[game->next_card], sizeof(card));
  game->next_card++;
  memcpy(game->community[1], game->deck[game->next_card], sizeof(card));
  game->next_card++;
  memcpy(game->community[2], game->deck[game->next_card], sizeof(card));
  game->next_card++;
}

void deal_turn(poker_game_state *game) {
  game->game_stage = poker_game_state::stage::TURN;
  // burn one card
  game->next_card++;

  memcpy(game->community[3], game->deck[game->next_card], sizeof(card));
  game->next_card++;
}

void deal_river(poker_game_state *game) {
  game->game_stage = poker_game_state::stage::RIVER;
  // burn one card
  game->next_card++;

  memcpy(game->community[4], game->deck[game->next_card], sizeof(card));
  game->next_card++;
}

void print_game_state(poker_game_state *game) {
  std::cout << "\n============================================\n";
  std::cout << "Game Stage: " << (int)game->game_stage
            << " | Pot: " << game->pot << "\n";
  std::cout << "Community: ";
  for (int i = 0; i < 5; i++) {
    if (game->community[i][0] != 0)
      std::cout << game->community[i] << " ";
    else
      std::cout << "[  ] ";
  }
  std::cout << "\n--------------------------------------------\n";

  for (int i = 0; i < game->num_players; i++) {
    std::cout << "P" << i;
    if (i == game->dealer_pos)
      std::cout << "(D)";
    if (i == (int)game->hero_pos)
      std::cout << "(HERO)";

    std::cout << " | Stack: " << game->stacks[i] << " | Bet: " << game->bets[i];

    if (game->folded[i]) {
      std::cout << " | FOLDED";
    } else {
      std::cout << " | Hand: ";
      // Reveal all hands at Showdown, otherwise only Hero's
      if (game->game_stage == poker_game_state::stage::SHOWDOWN ||
          i == (int)game->hero_pos) {
        std::cout << game->hands[i][0] << " " << game->hands[i][1];
      } else {
        std::cout << "XX XX";
      }
    }
    std::cout << "\n";
  }
  std::cout << "============================================\n";
}

void betting_round(poker_game_state *game) {
  int active_players = 0;
  for (int i = 0; i < game->num_players; i++)
    if (!game->folded[i])
      active_players++;
  if (active_players <= 1)
    return;

  // Reset bets for street if not preflop
  // In actual poker, previously matched bets go to pot. We emulate this by
  // resetting current street bets to 0 but Preflop is special because blinds
  // are live bets. For simplicity, we just track current street contribution in
  // bets[].

  if (game->game_stage != poker_game_state::stage::PREFLOP) {
    for (int i = 0; i < 9; i++)
      game->bets[i] = 0;
    game->current_bet = 0;
    game->current_player = (game->dealer_pos + 1) % game->num_players;
  } else {
    // Preflop: action starts left of BB (UTG)
    // Blinds already posted in play_game
    game->current_player = (game->dealer_pos + 3) % game->num_players;
  }

  int players_to_act = active_players;
  // Usually logic: continue until all active players have matched high bet and
  // had a chance to act.

  // Quick Hack: Just give everyone one chance to call/fold/raise unless a raise
  // happens. We restart the count if someone raises.

  while (players_to_act > 0) {
    int p = game->current_player;

    if (game->folded[p]) {
      game->current_player = (game->current_player + 1) % game->num_players;
      continue;
    }

    // Check if everyone else folded
    int current_active = 0;
    for (int i = 0; i < game->num_players; i++)
      if (!game->folded[i])
        current_active++;
    if (current_active == 1)
      return; // Winner found

    // Player turn
    if (p == (int)game->hero_pos) {
      print_game_state(game);
      std::cout << "Your turn! To Call: " << (game->current_bet - game->bets[p])
                << "\n";
      std::cout << "Action (c = call/check, r = raise, f = fold): ";
      char action;
      std::cin >> action;

      if (action == 'f') {
        game->folded[p] = true;
        std::cout << "You folded.\n";
      } else if (action == 'r') {
        int amount;
        std::cout << "Raise to total (min " << game->current_bet * 2 << "): ";
        std::cin >> amount;
        if (amount < game->current_bet * 2)
          amount = game->current_bet * 2;
        if (amount > game->stacks[p] + game->bets[p])
          amount = game->stacks[p] + game->bets[p]; // All in

        int added = amount - game->bets[p];
        game->stacks[p] -= added;
        game->bets[p] += added;
        game->pot += added;
        game->current_bet = amount;

        // Re-open betting for others
        players_to_act = current_active;
        std::cout << "You raised to " << amount << ".\n";
      } else {
        int to_call = game->current_bet - game->bets[p];
        if (to_call > game->stacks[p])
          to_call = game->stacks[p]; // All in call
        game->stacks[p] -= to_call;
        game->bets[p] += to_call;
        game->pot += to_call;
        std::cout << "You called/checked.\n";
      }
    } else {
      // Bot Logic: Always Call/Check
      int to_call = game->current_bet - game->bets[p];
      if (to_call > 0) {
        if (to_call > game->stacks[p])
          to_call = game->stacks[p];
        game->stacks[p] -= to_call;
        game->bets[p] += to_call;
        game->pot += to_call;
        std::cout << "Player " << p << " calls " << to_call << ".\n";
      } else {
        std::cout << "Player " << p << " checks.\n";
      }
    }

    players_to_act--;
    game->current_player = (game->current_player + 1) % game->num_players;
  }
}

static int parse_rank(char c) {
  if (c >= '2' && c <= '9')
    return c - '2';
  if (c == 'T')
    return 8;
  if (c == 'J')
    return 9;
  if (c == 'Q')
    return 10;
  if (c == 'K')
    return 11;
  if (c == 'A')
    return 12;
  return -1;
}

static int parse_suit(char c) {
  if (c == 'H')
    return 0;
  if (c == 'D')
    return 1;
  if (c == 'S')
    return 2;
  if (c == 'C')
    return 3;
  return -1;
}

static long long evaluate_5_cards(int r[], int s[]) {
  // sort ranks descending
  std::pair<int, int> cards[5];
  for (int i = 0; i < 5; ++i)
    cards[i] = {r[i], s[i]};
  std::sort(cards, cards + 5, [](auto a, auto b) { return a.first > b.first; });

  bool flush = true;
  for (int i = 1; i < 5; ++i)
    if (cards[i].second != cards[0].second)
      flush = false;

  bool straight = true;
  for (int i = 0; i < 4; ++i)
    if (cards[i].first != cards[i + 1].first + 1)
      straight = false;

  // Special ace low straight A, 5, 4, 3, 2 -> 12, 3, 2, 1, 0
  if (!straight && cards[0].first == 12 && cards[1].first == 3 &&
      cards[2].first == 2 && cards[3].first == 1 && cards[4].first == 0) {
    straight = true;
  }

  if (straight && flush) {
    if (cards[0].first == 12 && cards[1].first == 3)
      return (8LL << 20) | 3; // 5-high str flush
    return (8LL << 20) | cards[0].first;
  }

  // Counts
  int counts[13] = {0};
  for (int i = 0; i < 5; ++i)
    counts[cards[i].first]++;

  int quads = -1, trips = -1, pair1 = -1, pair2 = -1;
  for (int i = 12; i >= 0; --i) {
    if (counts[i] == 4)
      quads = i;
    else if (counts[i] == 3)
      trips = i;
    else if (counts[i] == 2) {
      if (pair1 == -1)
        pair1 = i;
      else
        pair2 = i;
    }
  }

  if (quads != -1) {
    int kicker = -1;
    for (int i = 0; i < 5; ++i)
      if (cards[i].first != quads)
        kicker = cards[i].first;
    return (7LL << 20) | (quads << 16) | (kicker << 12);
  }

  if (trips != -1 && pair1 != -1) {
    return (6LL << 20) | (trips << 16) | (pair1 << 12);
  }

  if (flush) {
    return (5LL << 20) | (cards[0].first << 16) | (cards[1].first << 12) |
           (cards[2].first << 8) | (cards[3].first << 4) | cards[4].first;
  }

  if (straight) {
    if (cards[0].first == 12 && cards[1].first == 3)
      return (4LL << 20) | 3;
    return (4LL << 20) | cards[0].first;
  }

  if (trips != -1) {
    int k1 = -1, k2 = -1;
    for (int i = 0; i < 5; ++i) {
      if (cards[i].first != trips) {
        if (k1 == -1)
          k1 = cards[i].first;
        else
          k2 = cards[i].first;
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
        if (k1 == -1)
          k1 = cards[i].first;
        else if (k2 == -1)
          k2 = cards[i].first;
        else
          k3 = cards[i].first;
      }
    }
    return (1LL << 20) | (pair1 << 16) | (k1 << 12) | (k2 << 8) | (k3 << 4);
  }

  return (long long)cards[0].first << 16 | (cards[1].first << 12) |
         (cards[2].first << 8) | (cards[3].first << 4) | cards[4].first;
}

void evaluate_winner(poker_game_state *game) {
  std::vector<int> active_players;
  for (int i = 0; i < game->num_players; ++i) {
    if (!game->folded[i])
      active_players.push_back(i);
  }

  if (active_players.size() == 1) {
    std::cout << "Winner: Player " << active_players[0]
              << " (Opponents folded)\n";
    game->stacks[active_players[0]] += game->pot;
    game->pot = 0;
    return;
  }

  long long best_score = -1;
  std::vector<int> winners;

  for (int p : active_players) {
    // Collect 7 cards
    std::vector<int> ranks;
    std::vector<int> suits;

    // Hole cards
    ranks.push_back(parse_rank(game->hands[p][0][0]));
    ranks.push_back(parse_rank(game->hands[p][1][0]));
    suits.push_back(parse_suit(game->hands[p][0][1]));
    suits.push_back(parse_suit(game->hands[p][1][1]));

    // Community cards
    for (int i = 0; i < 5; ++i) {
      ranks.push_back(parse_rank(game->community[i][0]));
      suits.push_back(parse_suit(game->community[i][1]));
    }

    // Find best 5-card hand
    long long current_best = -1;

    for (int i = 0; i < 7; ++i) {
      for (int j = i + 1; j < 7; ++j) {
        // exclude i and j
        int r[5], s[5];
        int idx = 0;
        for (int k = 0; k < 7; ++k) {
          if (k == i || k == j)
            continue;
          r[idx] = ranks[k];
          s[idx] = suits[k];
          idx++;
        }
        long long score = evaluate_5_cards(r, s);
        if (score > current_best)
          current_best = score;
      }
    }

    // Convert score type to readable string for debug
    int type = current_best >> 20;
    const char *type_names[] = {"High Card",  "Pair",     "Two Pair",
                                "Trips",      "Straight", "Flush",
                                "Full House", "Quads",    "Str Flush"};

    std::cout << "Player " << p << " Hand: " << type_names[type] << " ("
              << std::hex << current_best << std::dec << ")\n";

    if (current_best > best_score) {
      best_score = current_best;
      winners.clear();
      winners.push_back(p);
    } else if (current_best == best_score) {
      winners.push_back(p);
    }
  }

  if (winners.size() == 1) {
    std::cout << "Winner: Player " << winners[0] << "\n";
    game->stacks[winners[0]] += game->pot;
  } else {
    std::cout << "Split Pot between: ";
    int split_amt = game->pot / winners.size();
    for (int w : winners) {
      std::cout << "Player " << w << " ";
      game->stacks[w] += split_amt;
    }
    std::cout << "\n";
  }
  game->pot = 0;
}

void play_game(poker_game_state *game) {
  // 1. Post Blinds
  int sb_pos = (game->dealer_pos + 1) % game->num_players;
  int bb_pos = (game->dealer_pos + 2) % game->num_players;

  // SB
  game->stacks[sb_pos] -= game->small_blind;
  game->bets[sb_pos] = game->small_blind;
  game->pot += game->small_blind;

  // BB
  game->stacks[bb_pos] -= game->big_blind;
  game->bets[bb_pos] = game->big_blind;
  game->pot += game->big_blind;

  game->current_bet = game->big_blind;

  std::cout << "Blinds posted. SB: Player " << sb_pos << ", BB: Player "
            << bb_pos << "\n";

  // Preflop
  std::cout << "\n--- PREFLOP ---\n";
  betting_round(game);

  int active_count = 0;
  for (int i = 0; i < 9; i++)
    if (!game->folded[i])
      active_count++;
  if (active_count <= 1)
    goto end_hand;

  // Flop
  deal_flop(game);
  std::cout << "\n--- FLOP ---\n";
  print_game_state(game);
  betting_round(game);

  active_count = 0;
  for (int i = 0; i < 9; i++)
    if (!game->folded[i])
      active_count++;
  if (active_count <= 1)
    goto end_hand;

  // Turn
  deal_turn(game);
  std::cout << "\n--- TURN ---\n";
  print_game_state(game);
  betting_round(game);

  active_count = 0;
  for (int i = 0; i < 9; i++)
    if (!game->folded[i])
      active_count++;
  if (active_count <= 1)
    goto end_hand;

  // River
  deal_river(game);
  std::cout << "\n--- RIVER ---\n";
  print_game_state(game);
  betting_round(game);

end_hand:
  game->game_stage = poker_game_state::stage::SHOWDOWN;
  std::cout << "\n--- SHOWDOWN ---\n";
  print_game_state(game);
  evaluate_winner(game);
}