# player.py
from ball import Ball

PLAYER_COLORS = {
    1: (255, 255, 255),    # White
    2: (173, 216, 230)     # Light Blue
}

class PlayerManager:
    """Manages player turns, scores, and ball objects."""
    def __init__(self):
        self.num_players = 1
        self.current_player_idx = 1
        self.scores = {}
        self.finished_players = set()
        self.balls = {}

    def setup_new_game(self, num_players):
        """Initializes the manager for the start of a new game."""
        self.num_players = num_players
        self.current_player_idx = 1
        self.scores = {p: 0 for p in range(1, self.num_players + 1)}

    def prepare_for_level(self, start_pos):
        """Creates new balls and resets scores for a new level."""
        self.balls = {}
        for i in range(1, self.num_players + 1):
            color = PLAYER_COLORS.get(i, (255, 255, 255))
            self.balls[i] = Ball(pos=start_pos, color=color)
        
        self.scores = {p: 0 for p in range(1, self.num_players + 1)}
        self.finished_players = set()
        self.current_player_idx = 1

    def get_active_ball(self):
        """Returns the ball object for the current player."""
        return self.balls[self.current_player_idx]

    def record_shot(self):
        """Increments the stroke count for the current player."""
        self.scores[self.current_player_idx] += 1

    def finish_turn_for_player(self):
        """Marks the current player as finished for the hole."""
        self.get_active_ball().putt_in_hole()
        self.finished_players.add(self.current_player_idx)

    def all_players_finished(self):
        """Checks if all players have completed the hole."""
        return len(self.finished_players) == self.num_players

    def next_turn(self):
        """Switches to the next player who has not yet finished."""
        if self.all_players_finished():
            return

        # Loop to find the next player who is not in the finished set
        self.current_player_idx = (self.current_player_idx % self.num_players) + 1
        while self.current_player_idx in self.finished_players:
            self.current_player_idx = (self.current_player_idx % self.num_players) + 1