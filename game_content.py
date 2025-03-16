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
RANDOM_EVENTS = [
    {
        "title": "The Naked Sorcerer",
        "description": "A mysterious, completely unclothed sorcerer stands before you, holding a smoldering herb in one hand. 'Come, traveler,' he says, 'join me in the enchanted waters and cleanse your soul.'",
        "choices": [
            {
                "text": "Embrace the magic and dive in",
                "effect": {
                    "stamina": 50,
                    "reputation": -5
                }
            },
            {
                "text": "Politely decline and avert your eyes",
                "effect": {
                    "moves": 5,
                    "wisdom": 10
                }
            }
        ]
    },
    {
        "title": "The Alchemists' Festival",
        "description": "A group of alchemists is holding a grand potion festival. Two particular mixologists stand out—one with wild, untamed hair and another who swears their concoctions get stronger with each attempt.",
        "choices": [
            {
                "text": "Try their strongest elixir",
                "effect": {
                    "stamina": 40,
                    "magic": 50,
                    "balance": -10
                }
            },
            {
                "text": "Stick to water, just in case",
                "effect": {
                    "moves": 5,
                    "wisdom": 10
                }
            }
        ]
    },
    {
        "title": "The Noble Wedding",
        "description": "A noble wedding is taking place in a grand castle. The bride and groom are already exchanging vows, but the priest suddenly calls out, 'Wait! Who among you dares to challenge this union?'",
        "choices": [
            {
                "text": "Step forward and object dramatically",
                "effect": {
                    "reputation": 100,
                    "stamina": -30
                }
            },
            {
                "text": "Stay quiet and enjoy the feast",
                "effect": {
                    "stamina": 50,
                    "moves": 3
                }
            }
        ]
    },
    {
        "title": "The Hidden Grove",
        "description": "In a hidden grove, you find an opulent, steaming bath carved from marble. Two figures lounge within, goblets in hand, laughing as if lost in time. 'Join us, traveler!' one slurs. 'The water's perfect, and the wine never runs dry!'",
        "choices": [
            {
                "text": "Join them for a drink and a soak",
                "effect": {
                    "stamina": 60,
                    "moves": -5
                }
            },
            {
                "text": "Refuse and move on before you get trapped too",
                "effect": {
                    "moves": 3,
                    "resistance": 10
                }
            }
        ]
    }
]

def get_random_event():
    """Return a random event from the list of possible events"""
    return random.choice(RANDOM_EVENTS)

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