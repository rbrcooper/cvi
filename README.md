# The hunt for the Chateau

An interactive web-based game where players explore medieval European cities, solve riddles, and discover a mysterious château.

## Features
- Interactive map navigation using WASD controls
- City exploration and riddle solving
- Dynamic background music that changes with game progress
- Companion system with special characters
- Achievement tracking
- Mysterious location to discover

## Technical Stack
- Python/Flask backend
- HTML/CSS/JavaScript frontend
- Folium for map integration
- Geopy for distance calculations

## Deployment Instructions

### Local Development
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python app.py`

### Deployment on Render
1. Fork/push this repository to GitHub
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Use the following settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Python Version: 3.9 or higher

## Environment Variables
No environment variables are required for basic deployment.

## Game Assets
- Background music and mystery music are included in `static/music/`
- Images and other assets are in `static/`

## Gameplay

1. Choose your starting city from London, Paris, Berlin, Geneva, or Amsterdam
2. Each city presents a unique riddle about its medieval history
3. Solve riddles to progress to the next city
4. Face random events during your journey
5. Make choices that affect your progress
6. Track your journey through the cities
7. Discover the mysterious château at the end of your quest

## Technical Details

- Built with Python and Flask
- Uses Folium for map visualization
- Minimal JavaScript for essential interactivity
- Medieval-themed UI with custom styling
- Session-based progress tracking

## Contributing

Feel free to submit issues and enhancement requests! 
