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
from datetime import datetime

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
    try:
        if not init_game_state():
            flash("Error initializing game state. Please try again.", "error")
            return render_template("index.html", locations=CITIES.keys(), characters=CHARACTERS, version="1.1")

        if request.method == "POST":
            chosen_city = request.form.get("start_location")
            chosen_character = request.form.get("character")
            player_name = request.form.get("player_name")
            
            print(f"Received form data - City: {chosen_city}, Character: {chosen_character}, Name: {player_name}")
            
            if not player_name:
                flash("Please enter your name!", "error")
                return render_template("index.html", locations=CITIES.keys(), characters=CHARACTERS, version="1.1")
            
            if chosen_character not in CHARACTERS:
                flash("Please select a valid character!", "error")
                return render_template("index.html", locations=CITIES.keys(), characters=CHARACTERS, version="1.1")
                
            if chosen_city in CITIES:
                try:
                    if "game_state" not in session:
                        session["game_state"] = {}
                    
                    session["game_state"].update({
                        "current_city": chosen_city,
                        "player_position": CITIES[chosen_city].coordinates,
                        "character": chosen_character,
                        "player_name": player_name,
                        "moves": 0,
                        "riddles_solved": [],
                        "game_completed": False,
                        "in_city": True,
                        "score": {
                            "total": 0,
                            "riddles_solved": 0,
                            "efficiency_bonus": 0,
                            "wrong_answers": 0
                        },
                        "companions": [],
                        "stamina": 100.0,
                        "wrong_answers": {},
                        "has_died": False,
                        "death_message": "",
                        "total_cities": len(CITIES),
                        "total_distance": 0.0,
                        "last_riddle_moves": 0,
                        "achievements": {}
                    })
                    
                    session.modified = True
                    print(f"Game state initialized successfully: {session['game_state']}")
                    return redirect(url_for("game"))
                except Exception as e:
                    print(f"Error updating game state: {str(e)}")
                    flash(f"Error starting game: {str(e)}", "error")
                    return render_template("index.html", locations=CITIES.keys(), characters=CHARACTERS, version="1.1")
            else:
                flash("Invalid city selected!", "error")
        
        return render_template("index.html", locations=CITIES.keys(), characters=CHARACTERS, version="1.1")
    except Exception as e:
        print(f"Unexpected error in index route: {str(e)}")
        flash("An unexpected error occurred. Please try again.", "error")
        return render_template("index.html", locations=CITIES.keys(), characters=CHARACTERS, version="1.1")

@app.route("/move", methods=["POST"])
def move():
    try:
        if not session.get("game_state"):
            return jsonify({"error": "No active game"}), 400

        data = request.get_json()
        direction = data.get("direction", "").lower()
        current_pos = session["game_state"]["player_position"]
        
        # Store old position for distance calculation
        old_pos = current_pos.copy()
        
        # Update position based on direction
        if direction == "w":
            current_pos[1] += MOVEMENT_SPEED
        elif direction == "s":
            current_pos[1] -= MOVEMENT_SPEED
        elif direction == "a":
            current_pos[0] -= MOVEMENT_SPEED
        elif direction == "d":
            current_pos[0] += MOVEMENT_SPEED
        else:
            return jsonify({"error": "Invalid direction"}), 400

        # Apply character bonuses
        character = session["game_state"]["character"]
        if character in CHARACTERS:
            char_data = CHARACTERS[character]
            if direction in ["w", "s", "a", "d"]:
                current_pos[0] += char_data.get("movement_speed", 0)
                current_pos[1] += char_data.get("movement_speed", 0)
                session["game_state"]["stamina"] -= char_data.get("stamina_cost", 0.1)

        # Calculate distance traveled
        distance = geodesic(old_pos, current_pos).kilometers
        session["game_state"]["total_distance"] += distance
        session["game_state"]["moves"] += 1

        # Check if near château
        chateau_distance = geodesic(current_pos, CHATEAU_LOCATION).kilometers
        if chateau_distance < REVEAL_THRESHOLD:
            if not session["game_state"].get("chateau_revealed"):
                session["game_state"]["chateau_revealed"] = True
                # Save player data to leaderboard
                player_data = {
                    "name": session["game_state"]["player_name"],
                    "character": session["game_state"]["character"],
                    "score": session["game_state"]["score"]["total"],
                    "moves": session["game_state"]["moves"],
                    "distance": session["game_state"]["total_distance"],
                    "riddles_solved": len(session["game_state"]["riddles_solved"]),
                    "completion_time": session["game_state"]["moves"],
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                if "leaderboard" not in session:
                    session["leaderboard"] = []
                session["leaderboard"].append(player_data)
                
                # Mark game as completed
                session["game_state"]["game_completed"] = True
                
                return jsonify({
                    "position": current_pos,
                    "nearest_city": None,
                    "distance": 0,
                    "stamina": session["game_state"]["stamina"],
                    "score": session["game_state"]["score"],
                    "companions": session["game_state"]["companions"],
                    "chateau_revealed": True,
                    "game_completed": True,
                    "redirect": url_for("leaderboard")
                })

        # Check if near any city
        nearest_city, city_distance = get_nearest_city(current_pos[0], current_pos[1])
        
        # Update game state
        session["game_state"]["player_position"] = current_pos
        session.modified = True

        return jsonify({
            "position": current_pos,
            "nearest_city": nearest_city,
            "distance": city_distance,
            "stamina": session["game_state"]["stamina"],
            "score": session["game_state"]["score"],
            "companions": session["game_state"]["companions"],
            "chateau_revealed": session["game_state"].get("chateau_revealed", False),
            "game_completed": session["game_state"].get("game_completed", False)
        })

    except Exception as e:
        print(f"Error in move route: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
    try:
        # Check if game state exists
        if not session.get("game_state"):
            print("No game state found, initializing...")
            if not init_game_state():
                print("Failed to initialize game state")
                flash("Error initializing game state. Please start a new game.", "error")
                return redirect(url_for("index"))
        
        # Validate required game state data
        if not session["game_state"].get("current_city"):
            print("No current city found")
            flash("Please select a starting city.", "error")
            return redirect(url_for("index"))
            
        if not session["game_state"].get("character"):
            print("No character selected")
            flash("Please select a character.", "error")
            return redirect(url_for("index"))
        
        current_city = session["game_state"]["current_city"]
        print(f"Current city in game route: {current_city}")
        
        # Validate city exists in CITIES
        if current_city not in CITIES:
            print(f"Invalid city: {current_city}")
            flash("Invalid city selected. Please start a new game.", "error")
            return redirect(url_for("index"))
            
        city_data = CITIES[current_city]
        
        # Prepare template data with error handling
        template_data = {
            "city": city_data,
            "game_state": session["game_state"],
            "current_event": session["game_state"].get("current_event"),
            "CITIES": CITIES,
            "CHATEAU_LOCATION": CHATEAU_LOCATION,
            "ACHIEVEMENTS": ACHIEVEMENTS,
            "characters": CHARACTERS
        }
        
        print("Rendering game template with data:", template_data)
        return render_template("game.html", **template_data)
        
    except Exception as e:
        print(f"Error in game route: {str(e)}")
        flash("An error occurred while loading the game. Please try again.", "error")
        return redirect(url_for("index"))

@app.route("/reset")
def reset_game():
    session.clear()
    return redirect(url_for("index"))

@app.route("/leaderboard")
def leaderboard():
    try:
        # Get leaderboard data from session
        if "leaderboard" not in session:
            session["leaderboard"] = []
        
        # Sort by score and get top 10
        scores = sorted(session["leaderboard"], key=lambda x: x["score"], reverse=True)[:10]
        
        # Calculate some statistics
        total_players = len(session["leaderboard"])
        avg_score = sum(score["score"] for score in scores) / len(scores) if scores else 0
        avg_moves = sum(score["moves"] for score in scores) / len(scores) if scores else 0
        avg_distance = sum(score["distance"] for score in scores) / len(scores) if scores else 0
        
        stats = {
            "total_players": total_players,
            "avg_score": round(avg_score, 2),
            "avg_moves": round(avg_moves, 2),
            "avg_distance": round(avg_distance, 2)
        }
        
        return render_template(
            "leaderboard.html",
            scores=scores,
            stats=stats
        )
    except Exception as e:
        print(f"Error in leaderboard route: {str(e)}")
        flash("Error loading leaderboard. Please try again.", "error")
        return redirect(url_for("index"))

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
