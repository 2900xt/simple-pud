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
  memset(game->community, 0, sizeof(game->community));
  game->hero_pos = poker_game_state::position::SB;
  game->game_stage = poker_game_state::stage::PREFLOP;

  // shuffle deck
  unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
  std::mt19937 rng(seed);

  memcpy(game->deck, static_deck, sizeof(game->deck));
  std::shuffle(game->deck, game->deck + 52, rng);

  std::cout << "Deck Shuffled: ";
  debug_print_deck(game->deck, 52);

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
  std::cout << "Game State: " << std::endl;
  std::cout << "Num Players: " << game->num_players << std::endl;
  std::cout << "Hero Pos: " << (int)game->hero_pos << std::endl;
  std::cout << "Game Stage: " << (int)game->game_stage << std::endl;
  std::cout << "Hands: " << std::endl;
  for (int i = 0; i < game->num_players; i++) {
    std::cout << game->hands[i][0] << " " << game->hands[i][1] << std::endl;
  }
  std::cout << "Community: " << std::endl;
  for (int i = 0; i < 5; i++) {
    std::cout << game->community[i] << " ";
  }
  std::cout << std::endl;
}