from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Character:
    name: str
    icon: str
    bonus_description: str
    move_multiplier: float = 1.0
    riddle_hint_chance: float = 0.0
    event_bonus_chance: float = 0.0
    stamina_bonus: float = 0.0
    deadly_event_chance: float = 0.0  # Chance of deadly event occurring (1/5 = 0.2)
    deadly_event: str = ""  # Description of the deadly event

CHARACTERS = {
    "knight": Character(
        name="Random French guy",
        icon="🥖",
        bonus_description="80% chance of baguette",
        move_multiplier=1.2,
        deadly_event_chance=0.001,  # 0.01% chance
        deadly_event="Admits English cuisine is superior and dies from shame"
    ),
    "scholar": Character(
        name="Peasant",
        icon="🧑‍🌾",
        bonus_description="What you doing here bro?",
        riddle_hint_chance=-0.50,
        event_bonus_chance=-0.99,
        stamina_bonus=-0.3,
        deadly_event_chance=0.90,  # 0.03% chance (higher as it's the joke character)
        deadly_event="Dies of famine"
    ),
    "horse_rider": Character(
        name="Captin Horse",
        icon="🏇",
        bonus_description="Extra stamina for longer journeys, confusion is increased",
        stamina_bonus=0.3,
        deadly_event_chance=0.0001,  # 0.01% chance
        deadly_event="Becomes too confused and gallops off a cliff in a moment of disorientation"
    ),
    "noble": Character(
        name="King Louis IX",
        icon="👑",
        bonus_description="20% better chance at favorable event outcomes, chance of guillotine is increased",
        event_bonus_chance=0.2,
        deadly_event_chance=0.001,  # 0.% chance
        deadly_event="Encounters a peasant uprising and faces the guillotine"
    ),
    "archer": Character(
        name="Techno Goblin",
        icon="👺",
        bonus_description="Moves 20% faster, stamina is moderately impacted",
        move_multiplier=1.2,
        stamina_bonus=-0.2,
        deadly_event_chance=0.0001,  # 0.01% chance
        deadly_event="Uses up all disco biscuits and falls into eternal sleep"
    )
}

@dataclass
class Score:
    base_points: int = 0
    time_bonus: int = 0
    efficiency_bonus: int = 0
    event_bonus: int = 0
    wrong_answer_penalty: int = 0

    @property
    def total(self) -> int:
        return (self.base_points + 
                self.time_bonus + 
                self.efficiency_bonus + 
                self.event_bonus - 
                self.wrong_answer_penalty)

    def add_riddle_solved(self, moves_taken: int):
        """Add points for solving a riddle"""
        self.base_points += 1000
        self.time_bonus += max(0, (100 - moves_taken) * 10)

    def add_wrong_answer(self):
        """Add penalty for wrong riddle answer"""
        self.wrong_answer_penalty += 50

    def add_event_bonus(self, points: int):
        """Add bonus points from events"""
        self.event_bonus += points

@dataclass
class Achievement:
    name: str
    description: str
    icon: str
    points: int
    achieved: bool = False

ACHIEVEMENTS = {
    "first_riddle": Achievement(
        name="First Steps",
        description="Solve your first riddle",
        icon="🎯",
        points=100
    ),
    "speed_solver": Achievement(
        name="Quick Thinker",
        description="Solve a riddle in under 10 moves",
        icon="⚡",
        points=200
    ),
    "all_cities": Achievement(
        name="Master Explorer",
        description="Visit all cities",
        icon="🌟",
        points=500
    ),
    "efficient_route": Achievement(
        name="Path Finder",
        description="Complete the game in under 100 moves",
        icon="🗺️",
        points=300
    ),
    "event_master": Achievement(
        name="Fortune's Favorite",
        description="Successfully handle 3 random events",
        icon="🎲",
        points=200
    )
}

def calculate_efficiency_bonus(total_distance: float) -> int:
    """Calculate bonus points based on total distance traveled"""
    return max(0, int((1000 - total_distance) * 0.5))

def check_achievements(game_state: Dict) -> List[Achievement]:
    """Check and return newly achieved achievements"""
    new_achievements = []
    achievements = game_state.get("achievements", {})
    
    # First riddle achievement
    if (len(game_state["riddles_solved"]) >= 1 and 
        not achievements.get("first_riddle", {}).get("achieved")):
        new_achievements.append(ACHIEVEMENTS["first_riddle"])
    
    # Speed solver achievement
    if (game_state.get("last_riddle_moves", 100) < 10 and 
        not achievements.get("speed_solver", {}).get("achieved")):
        new_achievements.append(ACHIEVEMENTS["speed_solver"])
    
    # All cities achievement
    if (len(game_state["riddles_solved"]) == game_state["total_cities"] and 
        not achievements.get("all_cities", {}).get("achieved")):
        new_achievements.append(ACHIEVEMENTS["all_cities"])
    
    # Efficient route achievement
    if (game_state["moves"] < 100 and len(game_state["riddles_solved"]) > 0 and 
        not achievements.get("efficient_route", {}).get("achieved")):
        new_achievements.append(ACHIEVEMENTS["efficient_route"])
    
    # Event master achievement
    if (game_state.get("successful_events", 0) >= 3 and 
        not achievements.get("event_master", {}).get("achieved")):
        new_achievements.append(ACHIEVEMENTS["event_master"])
    
    return new_achievements 