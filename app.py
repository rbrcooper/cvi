from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import folium
from geopy.distance import geodesic
import os
import uuid
from game_content import (
    CITIES, get_random_event, check_riddle_answer, get_next_city,
    get_city_description, get_city_riddle, RANDOM_EVENTS
)
from game_mechanics import (
    CHARACTERS, Score, check_achievements, calculate_efficiency_bonus,
    ACHIEVEMENTS
)
import random

app = Flask(__name__)
# Use environment variable for secret key or generate a random one
app.secret_key = os.environ.get('FLASK_SECRET_KEY', str(uuid.uuid4()))
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session lifetime

# Error handler for 500 errors
@app.errorhandler(500)
def internal_error(error):
    # Clear the session if it might be corrupted
    session.clear()
    return render_template('error.html', error=str(error)), 500

# Error handler for 404 errors
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page not found"), 404

# Constants for mysterious location and château
MYSTERIOUS_LOCATION = [46.8566, 2.3522]  # Center of France
CHATEAU_LOCATION = [44.114833, 0.925222]    # Château de Goudourville coordinates
REVEAL_THRESHOLD = 25.0  # Match the city entry threshold

# Movement speed (in degrees)
MOVEMENT_SPEED = 0.1

# City entry threshold (in kilometers)
CITY_ENTRY_THRESHOLD = 25.0  # Increased from 15.0 to make it easier to trigger

def init_game_state():
    try:
        # Always create a new game state if it doesn't exist or if it's None
        if "game_state" not in session or session["game_state"] is None:
            session["game_state"] = {
                "current_city": None,
                "moves": 0,
                "riddles_solved": [],
                "game_completed": False,
                "player_position": None,
                "current_riddle": None,
                "in_city": False,
                "companions": [],  # List of player names who completed riddles
                "character": None,
                "player_name": None,
                "score": {
                    "total": 0,
                    "riddles_solved": 0,
                    "efficiency_bonus": 0,
                    "wrong_answers": 0
                },
                "achievements": {},
                "total_distance": 0.0,
                "last_riddle_moves": 0,
                "total_cities": len(CITIES),
                "stamina": 100.0,
                "wrong_answers": {},
                "has_died": False,
                "death_message": ""
            }
            print("Initialized new game state")
    except Exception as e:
        print(f"Error initializing game state: {str(e)}")
        session.clear()
        return False
    return True

def get_nearest_city(lat, lon):
    """Find the nearest city to the player's position"""
    min_distance = float('inf')
    nearest_city = None
    
    for city_name, city in CITIES.items():
        distance = geodesic((lat, lon), city.coordinates).kilometers
        print(f"Distance to {city_name}: {distance:.2f}km")
        if distance < min_distance:
            min_distance = distance
            nearest_city = city_name
    
    print(f"Nearest city: {nearest_city}, Distance: {min_distance:.2f}km")
    return nearest_city, min_distance

@app.route("/", methods=["GET", "POST"])
def index():
    init_game_state()
    if request.method == "POST":
        chosen_city = request.form.get("start_location")
        chosen_character = request.form.get("character")
        player_name = request.form.get("player_name")
        
        if not player_name:
            flash("Please enter your name!", "error")
            return render_template("index.html", locations=CITIES.keys(), characters=CHARACTERS, version="1.1")
        
        if chosen_character not in CHARACTERS:
            flash("Please select a valid character!", "error")
            return render_template("index.html", locations=CITIES.keys(), characters=CHARACTERS, version="1.1")
            
        if chosen_city in CITIES:
            session["game_state"]["current_city"] = chosen_city
            session["game_state"]["player_position"] = CITIES[chosen_city].coordinates
            session["game_state"]["character"] = chosen_character
            session["game_state"]["player_name"] = player_name
            session["game_state"]["moves"] = 0
            session["game_state"]["riddles_solved"] = []
            session["game_state"]["game_completed"] = False
            session["game_state"]["in_city"] = True
            session["game_state"]["score"] = {
                "total": 0,
                "riddles_solved": 0,
                "efficiency_bonus": 0,
                "wrong_answers": 0
            }
            session["game_state"]["companions"] = []
            session.modified = True
            return redirect(url_for("game"))
        else:
            flash("Invalid city selected!", "error")
    
    return render_template("index.html", locations=CITIES.keys(), characters=CHARACTERS, version="1.1")

@app.route("/move", methods=["POST"])
def move():
    if 'game_state' not in session:
        init_game_state()

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400

    # Get the character's bonuses
    character = CHARACTERS.get(session['game_state']['character'])
    if not character:
        return jsonify({'error': 'Invalid character'}), 400

    # Get current position
    if not session["game_state"]["player_position"]:
        return jsonify({"error": "Game not started"}), 400
    
    current_lat, current_lon = session["game_state"]["player_position"]
    
    # Apply character's move multiplier
    move_multiplier = character.move_multiplier
    stamina_bonus = character.stamina_bonus
    adjusted_speed = MOVEMENT_SPEED * move_multiplier
    
    # Update position based on movement type
    if 'direction' in data:
        # WASD movement
        direction = data['direction'].lower()
        stamina = session["game_state"]["stamina"]
        
        # Apply slower movement when tired
        if stamina < 20:
            adjusted_speed *= 0.5
        
        # Store old position for distance calculation
        old_position = (current_lat, current_lon)
        
        if direction == "w":
            current_lat += adjusted_speed
        elif direction == "s":
            current_lat -= adjusted_speed
        elif direction == "a":
            current_lon -= adjusted_speed
        elif direction == "d":
            current_lon += adjusted_speed
        
        # Update position
        session["game_state"]["player_position"] = [current_lat, current_lon]
        session["game_state"]["moves"] += 1
        
        # Check for rare deadly events
        if not session["game_state"].get("has_died", False):  # Only check if haven't died yet
            if random.random() < character.deadly_event_chance:
                session["game_state"]["has_died"] = True
                session["game_state"]["death_message"] = character.deadly_event
                return jsonify({
                    "success": False,
                    "game_over": True,
                    "message": f"Oh no! {character.deadly_event}",
                    "position": [current_lat, current_lon]
                })
        
        # Update stamina
        stamina_cost = 0.2  # Base stamina cost
        if stamina > 0:
            adjusted_cost = stamina_cost * (1.0 - stamina_bonus)
            session["game_state"]["stamina"] = max(0, stamina - adjusted_cost)
        
        # Stamina regeneration
        if random.random() < 0.15:
            base_regen = 10
            bonus_regen = base_regen * (1.0 + stamina_bonus)
            session["game_state"]["stamina"] = min(100, session["game_state"]["stamina"] + bonus_regen)
        
        # Calculate distance traveled
        distance = geodesic(old_position, (current_lat, current_lon)).kilometers
        session["game_state"]["total_distance"] += distance
    else:
        return jsonify({'error': 'Invalid movement data'}), 400
    
    # Check if player is near a city
    nearest_city, distance_to_city = get_nearest_city(current_lat, current_lon)
    in_city = distance_to_city < CITY_ENTRY_THRESHOLD
    
    # Check for mysterious location
    mysterious_location_reached = False
    chateau_revealed = False
    at_chateau = False
    
    # Check if all cities have been visited
    all_cities_visited = len(session["game_state"]["riddles_solved"]) >= len(CITIES)
    if all_cities_visited:
        session["game_state"]["mysterious_location_revealed"] = True
        mysterious_location = MYSTERIOUS_LOCATION  # Use the constant defined at the top
        distance_to_mystery = geodesic((current_lat, current_lon), mysterious_location).kilometers
        if distance_to_mystery < CITY_ENTRY_THRESHOLD:
            mysterious_location_reached = True
            session["game_state"]["chateau_revealed"] = True
            chateau_revealed = True
            
        # Check if player is at the château location
        if session["game_state"].get("chateau_revealed", False):
            distance_to_chateau = geodesic((current_lat, current_lon), CHATEAU_LOCATION).kilometers
            if distance_to_chateau < CITY_ENTRY_THRESHOLD:
                session["game_state"]["at_chateau"] = True
                at_chateau = True
    
    # Update city status
    if in_city and not session["game_state"]["in_city"]:
        session["game_state"]["current_city"] = nearest_city
        session["game_state"]["in_city"] = True
        # Only set the current_riddle if the city hasn't been solved yet
        if nearest_city not in session["game_state"]["riddles_solved"]:
            session["game_state"]["current_riddle"] = CITIES[nearest_city].riddle
        else:
            session["game_state"]["current_riddle"] = None
    elif not in_city and session["game_state"]["in_city"]:
        session["game_state"]["in_city"] = False
        session["game_state"]["current_riddle"] = None
        session["game_state"]["current_city"] = None

    session.modified = True
    
    # Prepare response
    response_data = {
        "success": True,
        "position": [current_lat, current_lon],
        "nearest_city": nearest_city,
        "distance": distance_to_city,
        "stamina": session["game_state"]["stamina"],
        "score": session["game_state"]["score"]["total"],
        "companions": session["game_state"]["companions"],
        "mysterious_location_revealed": session["game_state"].get("mysterious_location_revealed", False),
        "mysterious_location": MYSTERIOUS_LOCATION if session["game_state"].get("mysterious_location_revealed", False) else None,
        "mysterious_location_reached": mysterious_location_reached,
        "chateau_revealed": chateau_revealed,
        "chateau_location": CHATEAU_LOCATION if chateau_revealed else None,
        "at_chateau": at_chateau,
        "moves": session["game_state"]["moves"],
        "cities_visited": len(session["game_state"]["riddles_solved"]),
        "total_cities": len(CITIES),
        "current_city": session["game_state"]["current_city"],
        "in_city": in_city,
        "current_riddle": session["game_state"]["current_riddle"] if in_city and nearest_city not in session["game_state"]["riddles_solved"] else None
    }
    
    return jsonify(response_data)

@app.route("/handle_event", methods=["POST"])
def handle_event():
    """Handle player choices for random events"""
    if not session.get("game_state", {}).get("current_event"):
        return jsonify({"error": "No active event"}), 400

    choice = request.json.get("choice")
    if not choice:
        return jsonify({"error": "No choice provided"}), 400

    event = session["game_state"]["current_event"]
    chosen_effect = next((c["effect"] for c in event["choices"] if c["text"] == choice), None)
    
    if chosen_effect:
        # Apply move effects (more significant penalties/bonuses)
        if "moves" in chosen_effect:
            session["game_state"]["moves"] += chosen_effect["moves"]
        
        # Apply stamina effects (more impactful)
        if "stamina" in chosen_effect:
            current_stamina = session["game_state"]["stamina"]
            session["game_state"]["stamina"] = max(0, min(100, current_stamina + chosen_effect["stamina"]))
            
            # If stamina drops to 0, force player to rest (add moves penalty)
            if session["game_state"]["stamina"] <= 0:
                session["game_state"]["moves"] += 20  # Significant rest penalty
                session["game_state"]["stamina"] = 30  # Partial recovery after rest
        
        # Apply score effects (more significant)
        if "score" in chosen_effect:
            score = Score(**session["game_state"]["score"])
            score.add_event_bonus(chosen_effect["score"])
            session["game_state"]["score"] = score.__dict__
        
        # Apply position effects (new)
        if "position_change" in chosen_effect:
            current_lat, current_lon = session["game_state"]["player_position"]
            lat_change, lon_change = chosen_effect["position_change"]
            session["game_state"]["player_position"] = (current_lat + lat_change, current_lon + lon_change)
        
        # Apply riddle hint effect
        if "next_riddle_hint" in chosen_effect:
            session["game_state"]["next_riddle_hint"] = chosen_effect["next_riddle_hint"]
        
        session["game_state"]["successful_events"] += 1

    # Clear the current event
    session["game_state"]["current_event"] = None
    session.modified = True

    return jsonify({
        "success": True,
        "moves": session["game_state"]["moves"],
        "stamina": session["game_state"]["stamina"],
        "score": session["game_state"]["score"]["total"] if "score" in session["game_state"] else 0,
        "position": session["game_state"]["player_position"]  # Return updated position
    })

@app.route("/solve_riddle", methods=["POST"])
def solve_riddle():
    if "game_state" not in session:
        return jsonify({"success": False, "message": "Game not started"})

    data = request.get_json()
    if not data or "answer" not in data:
        return jsonify({"success": False, "message": "No answer provided"})

    current_city = session["game_state"]["current_city"]
    if not current_city:
        return jsonify({"success": False, "message": "No active riddle"})

    # Check if riddle was already solved
    if current_city in session["game_state"]["riddles_solved"]:
        return jsonify({"success": False, "message": "This riddle has already been solved"})

    answer = data["answer"].strip().lower()
    if check_riddle_answer(current_city, answer):
        # Add the city to solved riddles if not already there
        if current_city not in session["game_state"]["riddles_solved"]:
            session["game_state"]["riddles_solved"].append(current_city)
            
            # Special handling for Geneva - add Topsy the dog
            special_message = ""
            if current_city == "Geneva":
                if "🐕 Topsy" not in session["game_state"]["companions"]:
                    session["game_state"]["companions"].append("🐕 Topsy")
                    special_message = "You've found a new friend! Topsy the dog joins your journey. 🐕"
            
            # Check if all cities have been visited
            all_cities_visited = len(session["game_state"]["riddles_solved"]) >= len(CITIES)
            if all_cities_visited:
                session["game_state"]["mysterious_location_revealed"] = True
                if not special_message:
                    special_message = "All cities completed! A mysterious location has appeared in the center of France..."
            
            # Update score
            session["game_state"]["score"]["riddles_solved"] += 100
            session["game_state"]["score"]["total"] += 100
            
            # Clear the current riddle since it's solved
            session["game_state"]["current_riddle"] = None
            
            # Get the response message
            message = special_message if special_message else f"Correct! You've solved the riddle of {current_city}!"
            
            session.modified = True
            
            return jsonify({
                "success": True,
                "message": message,
                "cities_visited": len(session["game_state"]["riddles_solved"]),
                "total_cities": len(CITIES),
                "companions": session["game_state"]["companions"],
                "mysterious_location_revealed": session["game_state"].get("mysterious_location_revealed", False),
                "mysterious_location": MYSTERIOUS_LOCATION if session["game_state"].get("mysterious_location_revealed", False) else None,
                "score": session["game_state"]["score"]["total"]
            })
    else:
        # Track wrong answers and update score
        city_wrongs = session["game_state"]["wrong_answers"].get(current_city, 0) + 1
        session["game_state"]["wrong_answers"][current_city] = city_wrongs
        
        # Update wrong answers score penalty
        session["game_state"]["score"]["wrong_answers"] -= 10
        session["game_state"]["score"]["total"] -= 10
        
        return jsonify({
            "success": False,
            "message": "Incorrect answer. Try again!",
            "score": session["game_state"]["score"]["total"]
        })

@app.route("/game", methods=["GET", "POST"])
def game():
    if not session.get("game_state"):
        init_game_state()
    
    if not session.get("game_state", {}).get("current_city"):
        print("No city selected, redirecting to index")
        return redirect(url_for("index"))

    current_city = session["game_state"]["current_city"]
    print(f"Current city in game route: {current_city}")
    city_data = CITIES[current_city]

    # Ensure character is available
    if not session["game_state"].get("character"):
        return redirect(url_for("index"))

    return render_template(
        "game.html",
        city=city_data,
        game_state=session["game_state"],
        current_event=session["game_state"]["current_event"],
        CITIES=CITIES,
        CHATEAU_LOCATION=CHATEAU_LOCATION,
        ACHIEVEMENTS=ACHIEVEMENTS,
        characters=CHARACTERS
    )

@app.route("/reset")
def reset_game():
    session.clear()
    return redirect(url_for("index"))

@app.route("/leaderboard")
def leaderboard():
    # Implement proper leaderboard storage (e.g., in a database)
    # For now, we'll use a simple in-memory list
    if "leaderboard" not in session:
        session["leaderboard"] = []
    
    return render_template(
        "leaderboard.html",
        scores=sorted(session["leaderboard"], key=lambda x: x["score"], reverse=True)[:10]
    )

@app.route("/map")
def map_view():
    """Serve the map template"""
    return render_template(
        "map.html",
        game_state=session.get("game_state", {}),
        CITIES=CITIES,
        CHATEAU_LOCATION=CHATEAU_LOCATION,
        characters=CHARACTERS
    )

@app.route('/check_location')
def check_location():
    lat = float(request.args.get('lat'))
    lon = float(request.args.get('lon'))
    
    # Get game state
    game_state = session.get("game_state", {})
    all_cities_visited = len(game_state.get("riddles_solved", [])) >= len(CITIES)
    
    # Calculate distances
    mysterious_distance = geodesic((lat, lon), MYSTERIOUS_LOCATION).kilometers
    chateau_distance = geodesic((lat, lon), CHATEAU_LOCATION).kilometers
    
    # Initialize response
    response = {
        'mysterious_location': MYSTERIOUS_LOCATION if all_cities_visited else None,
        'show_mysterious': all_cities_visited,
        'show_chateau': False,
        'chateau_location': None,
        'show_popup': False,
        'message': None
    }
    
    # If player is close to mysterious location and has visited all cities
    if all_cities_visited and mysterious_distance <= REVEAL_THRESHOLD:
        response['show_mysterious'] = False
        response['show_chateau'] = True
        response['chateau_location'] = CHATEAU_LOCATION
        response['message'] = "A new location has been revealed on the map..."
        session["game_state"]["chateau_revealed"] = True
        
        # If player is also close to actual château
        if chateau_distance <= REVEAL_THRESHOLD:
            response['show_popup'] = True
            session["game_state"]["at_chateau"] = True
            response['message'] = "You've discovered the hidden Château!"
    
    session.modified = True
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
