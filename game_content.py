import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass
class City:
    name: str
    coordinates: Tuple[float, float]
    description: str
    riddle: str
    riddle_answer: str
    difficulty: int  # 1-5, increasing difficulty

@dataclass
class Event:
    title: str
    description: str
    choices: List[Dict]

# City definitions
CITIES = {
    "London": City(
        name="London",
        coordinates=(51.5074, -0.1278),
        description="Hear ye hear ye welcom' t' Lodonon",
        riddle="I have a bed, but I do not sleep. I have a mouth, but I don't eat. You hear me whisper, but I never talk. You can see me run, I never walk. What am I?",
        riddle_answer="river",
        difficulty=1
    ),
    "Amsterdam": City(
        name="Amsterdam",
        coordinates=(52.3676, 4.9041),
        description="A city of canals and bicycles, where historic architecture meets modern life.",
        riddle="What has keys, but no locks; space, but no room; and you can enter, but not go in?",
        riddle_answer="keyboard",
        difficulty=2
    ),
    "Paris": City(
        name="Paris",
        coordinates=(48.8566, 2.3522),
        description="The City of Light, where art and culture flourish along the Seine.",
        riddle="I am always hungry; I must always be fed. The finger I touch, will soon turn red. What am I?",
        riddle_answer="fire",
        difficulty=3
    ),
    "Berlin": City(
        name="Berlin",
        coordinates=(52.5200, 13.4050),
        description="A city of history and renewal, where the past and present intertwine.",
        riddle="Who makes it, has no need of it. Who buys it, has no use for it. Who uses it can neither see nor feel it. What is it?",
        riddle_answer="coffin",
        difficulty=4
    ),
    "Geneva": City(
        name="Geneva",
        coordinates=(46.2044, 6.1432),
        description="A city of diplomacy and watchmaking, nestled by a beautiful lake.",
        riddle="I have a face but no eyes, hands but no arms. What am I?",
        riddle_answer="clock",
        difficulty=5
    )
}

# Random events that can occur during travel
EVENTS = [
    Event(
        title="Storm on the Horizon",
        description="Dark clouds gather overhead, and thunder rumbles in the distance. The air grows heavy with the promise of a fierce storm.",
        choices=[
            {
                "text": "Seek shelter in a nearby tavern (Rest until morning)",
                "consequence": "rest",
                "effect": {"moves": 5, "stamina": 50}  # Lose 5 moves but gain 50 stamina
            },
            {
                "text": "Press on through the storm",
                "consequence": "brave",
                "effect": {"stamina": -30}  # Lose 30 stamina but no time penalty
            }
        ]
    ),
    Event(
        title="Mysterious Wanderer",
        description="A cloaked figure approaches, offering to share ancient knowledge of these lands.",
        choices=[
            {
                "text": "Stop to listen to their tales",
                "consequence": "wisdom",
                "effect": {"moves": 3, "next_riddle_hint": True}  # Lose 3 moves but get hint on next riddle
            },
            {
                "text": "Politely decline and continue your journey",
                "consequence": "cautious",
                "effect": {"stamina": 10}  # Small stamina boost for being cautious
            }
        ]
    ),
    Event(
        title="Bandit Ambush",
        description="A group of bandits emerges from the shadows, blocking your path!",
        choices=[
            {
                "text": "Stand and fight",
                "consequence": "fight",
                "effect": {"stamina": -40, "score": 100}  # Lose stamina but gain bonus points
            },
            {
                "text": "Attempt to flee",
                "consequence": "flee",
                "effect": {"moves": 4, "stamina": -20}  # Lose some moves and stamina
            }
        ]
    ),
    Event(
        title="Village Festival",
        description="You come across a small village celebrating their harvest festival. The aroma of food and sound of music fills the air.",
        choices=[
            {
                "text": "Join the festivities",
                "consequence": "festival",
                "effect": {"moves": 4, "stamina": 40, "score": 50}  # Time penalty but good rewards
            },
            {
                "text": "Continue your quest",
                "consequence": "focused",
                "effect": {"moves": -1}  # Small move bonus for staying focused
            }
        ]
    ),
    Event(
        title="Ancient Shrine",
        description="You discover an ancient shrine, its stones covered in mysterious runes.",
        choices=[
            {
                "text": "Stop to meditate",
                "consequence": "meditate",
                "effect": {"moves": 2, "stamina": 60}  # Time penalty but major stamina boost
            },
            {
                "text": "Leave it be",
                "consequence": "ignore",
                "effect": {"moves": -2}  # Small move bonus
            }
        ]
    )
]

def get_random_event() -> Event:
    """Return a random event from the list of possible events"""
    return random.choice(EVENTS)

def check_riddle_answer(city_name: str, answer: str) -> bool:
    """Check if the given answer matches the city's riddle answer."""
    valid_answers = {
        "clock": ["clock", "a clock", "the clock"],
    }
    
    answer = answer.lower().strip()
    correct_answer = CITIES[city_name].riddle_answer.lower()
    
    if correct_answer == "clock":
        return answer in valid_answers["clock"]
    
    return answer == correct_answer

def get_next_city(current_city: str, solved_cities: List[str]) -> str:
    """Get the next city to visit based on difficulty progression."""
    current_difficulty = CITIES[current_city].difficulty
    available_cities = [
        city for city, data in CITIES.items()
        if city not in solved_cities and data.difficulty > current_difficulty
    ]
    return min(available_cities, key=lambda x: CITIES[x].difficulty) if available_cities else None

def get_city_description(city_name: str) -> str:
    """Get the description of a city."""
    return CITIES[city_name].description

def get_city_riddle(city_name: str) -> str:
    """Get the riddle for a city."""
    return CITIES[city_name].riddle 