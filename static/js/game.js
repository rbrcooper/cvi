
let canMove = true;
let lastMoveTime = 0;
const moveDelay = 100; // Minimum delay between moves in milliseconds

window.addEventListener('load', async () => {
    try {
        const response = await fetch('/state');
        const state = await response.json();
        console.log('Game State:', state);
    } catch (error) {
        console.error('Error fetching game state:', error);
    }
});


// Handle keyboard controls globally
document.addEventListener('keydown', function(e) {
    // Only block movement if we're in a modal or actively typing in an input/textarea
    const activeElement = document.activeElement;
    const isTyping = activeElement && (
        activeElement.tagName === 'INPUT' ||
        activeElement.tagName === 'TEXTAREA' ||
        activeElement.isContentEditable
    );
    
    if (!canMove || isTyping) return;
    
    const key = e.key.toLowerCase();
    if (['w', 'a', 's', 'd'].includes(key)) {
        e.preventDefault(); // Prevent page scrolling
        
        // Rate limit the movement
        const now = Date.now();
        if (now - lastMoveTime >= moveDelay) {
            move(key);
            lastMoveTime = now;
        }
    }
});

// Add focus handling to ensure map controls work even when iframe loses focus
const mapIframe = document.querySelector('.map-container iframe');
if (mapIframe) {
    // When clicking anywhere except inputs, ensure the map can still receive keyboard events
    document.addEventListener('click', function(e) {
        const clickedElement = e.target;
        const isInput = clickedElement.tagName === 'INPUT' || 
                        clickedElement.tagName === 'TEXTAREA' || 
                        clickedElement.isContentEditable;
        
        if (!isInput) {
            // Remove focus from any focused element
            if (document.activeElement) {
                document.activeElement.blur();
            }
        }
    });
}

// Handle button clicks
document.querySelectorAll('.controls button').forEach(button => {
    button.addEventListener('click', function() {
        const direction = this.textContent.toLowerCase();
        if (canMove) {
            move(direction);
        }
    });
});

// Handle WASD movement
function move(direction) {
    if (!canMove) return;
    
    fetch('/move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ direction: direction })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showMessage(data.error, "error");
            return;
        }

        // Update player position on the map
        if (data.position) {
            const iframe = document.querySelector('iframe');
            if (iframe) {
                iframe.contentWindow.postMessage({
                    type: 'updatePosition',
                    lat: data.position[0],
                    lon: data.position[1]
                }, '*');
            }
        }

        // Update nearest city and distance
        if (data.nearest_city) {
            document.getElementById('distance').textContent = 
                `${Math.round(data.distance * 100) / 100} km`;
            document.getElementById('status').textContent = `Near ${data.nearest_city}`;
        } else {
            document.getElementById('status').textContent = 'Exploring...';
        }

        // Update stamina
        if (data.stamina !== undefined) {
            updateStaminaBar(data.stamina);
        }

        // Update score
        if (data.score !== undefined) {
            document.getElementById('score-counter').textContent = data.score;
        }

        // Update moves counter
        if (data.moves !== undefined) {
            document.getElementById('moves-counter').textContent = data.moves;
        }

        // Update cities visited
        if (data.cities_visited !== undefined && data.total_cities !== undefined) {
            document.getElementById('main-cities-count').textContent = `${data.cities_visited}/${data.total_cities}`;
            document.getElementById('cities-visited').textContent = `${data.cities_visited}/${data.total_cities}`;
        }

        // Update current location
        if (data.current_city) {
            document.getElementById('main-current-location').textContent = data.current_city;
            document.getElementById('current-location').textContent = data.current_city;
        }

        // Handle château reveal
        if (data.chateau_revealed) {
            document.getElementById('chateau-reveal').style.display = 'flex';
            handleMysteriousLocation(data);
        }

        // Handle château arrival
        if (data.at_chateau) {
            // document.getElementById('chateau-arrival').style.display = 'flex';
            handleMysteriousLocation(data);
        }

        // Handle game completion
        if (data.game_completed && data.redirect) {
            showMessage("Congratulations! You have completed your quest!", "success");
            setTimeout(() => {
                window.location.href = data.redirect;
            }, 2000);
        }

        // Handle city entry and riddle
        if (data.in_city && data.current_riddle) {
            handleCityEntry(data);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('An error occurred while moving', 'error');
    });
}

// Handle city entry
function handleCityEntry(data) {
    if (!data.current_riddle) return;  // Don't show modal if no riddle
    
    const modal = document.getElementById('riddleSection');
    const overlay = document.getElementById('modalOverlay');
    const input = document.getElementById('riddleAnswer');
    
    document.getElementById('cityName').textContent = data.nearest_city;
    document.getElementById('riddleText').textContent = data.current_riddle;
    
    // Show both the overlay and the modal
    overlay.style.display = 'block';
    modal.style.display = 'block';
    
    // Disable movement
    canMove = false;
    document.querySelector('.controls').classList.add('disabled');
    
    // Clear and focus the input
    input.value = '';
    input.focus();
}

// Update stamina bar with transition
function updateStaminaBar(stamina) {
    const staminaFill = document.getElementById('stamina-fill');
    if (staminaFill) {
        staminaFill.style.width = stamina + '%';
        staminaFill.style.backgroundColor = 
            stamina > 60 ? '#4CAF50' :
            stamina > 30 ? '#FFC107' :
            '#F44336';
    }
}

// Show event modal
function showEventModal(event) {
    const eventModal = document.getElementById('event-modal');
    document.getElementById('event-modal-title').textContent = event.title;
    document.getElementById('event-modal-description').textContent = event.description;
    
    const choicesDiv = document.getElementById('event-modal-choices');
    choicesDiv.innerHTML = '';
    event.choices.forEach(choice => {
        const button = document.createElement('button');
        button.textContent = choice.text;
        button.onclick = () => handleEventChoice(choice.text);
        choicesDiv.appendChild(button);
    });
    
    eventModal.style.display = 'flex';
    canMove = false;
    document.querySelector('.controls').classList.add('disabled');
}

// Handle event choices
function handleEventChoice(choice) {
    fetch('/handle_event', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ choice: choice })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update game state
            document.getElementById('moves').textContent = data.moves;
            updateStaminaBar(data.stamina);
            
            // Update stats box
            document.getElementById('cities-visited').textContent = `${data.cities_visited}/${data.total_cities}`;
            document.getElementById('current-location').textContent = data.current_city || "Exploring";
            document.getElementById('moves-counter').textContent = data.moves;
            document.getElementById('score-counter').textContent = data.score;
            
            // Update companions list
            const companionsList = document.getElementById('companions-list');
            if (data.companions && data.companions.length > 0) {
                companionsList.innerHTML = data.companions
                    .map(companion => `<div class="companion">${companion}</div>`)
                    .join('');
            } else {
                companionsList.innerHTML = '<p>No companions yet</p>';
            }
            
            // Hide event modal and re-enable movement
            const eventModal = document.getElementById('event-modal');
            eventModal.style.display = 'none';
            canMove = true;
            document.querySelector('.controls').classList.remove('disabled');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Also hide modal and re-enable movement on error
        document.getElementById('event-modal').style.display = 'none';
        canMove = true;
        document.querySelector('.controls').classList.remove('disabled');
    });
}

// Handle mysterious location and chateau
function handleMysteriousLocation(data) {
    const iframe = document.querySelector('iframe');
    if (!iframe) return;

    // Handle mysterious location reveal
    // if (data.mysterious_location_revealed && data.mysterious_location) {
    //     iframe.contentWindow.postMessage({
    //         type: 'revealMysteriousLocation',
    //         location: data.mysterious_location
    //     }, '*');
    // }
    
    // Handle chateau reveal
    if (data.chateau_revealed && data.chateau_location) {
        iframe.contentWindow.postMessage({
            type: 'revealChateau',
            location: data.chateau_location
        }, '*');
        
        // Show the chateau reveal modal
        document.getElementById('chateau-reveal').style.display = 'flex';
    }

    // Handle arrival at the chateau
    if (data.at_chateau) {
        // Show the chateau arrival modal with the image and links
        document.getElementById('chateau-arrival').style.display = 'flex';
        
        // Update the chateau content
        const chateauContent = document.querySelector('#chateau-arrival .chateau-content');
        chateauContent.innerHTML = `
            <h2>The Château Awaits!</h2>
            <p class="chateau-message">
                VICTORY! The Château has been revealed! Your journey, sacrifices and commitment all through your life has led you to this one specific moment.
                Make your way to the château to suckle on its sweet summer fruit...
            </p>
            <div class="chateau-links">
                <p>Learn more about the Château de Goudourville:</p>
                <a href="https://www.chateau-goudourville.fr/" target="_blank" class="btn btn-primary">Official Website</a>
                <a href="https://maps.app.goo.gl/m5Ep9KhAQdacWRLd7" target="_blank" class="btn btn-primary">View on Google Maps</a>
            </div>
            <img src="/static/chateau_mist.jpg" alt="Château in the mist" class="chateau-image" style="max-width: 100%; margin-top: 20px;">
            <button onclick="completeGameAndRedirect()" class="btn btn-primary">Complete Your Quest</button>
        `;
    }
}

// Add function to handle game completion and redirection
function completeGameAndRedirect() {
    fetch('/complete_game', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage("Congratulations! Your quest is complete!", "success");
            setTimeout(() => {
                window.location.href = '/leaderboard';
            }, 2000);
        } else {
            showMessage("Error completing the game", "error");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage("Error completing the game", "error");
    });
}

// Helper function to calculate distance
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
        Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// Update the solve_riddle function to handle the modal properly
function handleRiddleSubmit(event) {
    if (event) event.preventDefault();
    const answer = document.getElementById('riddleAnswer').value.trim().toLowerCase();
    
    if (!answer) {
        showMessage('Please enter an answer', 'error');
        return;
    }
    
    fetch('/solve_riddle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ answer: answer })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update cities visited count
            document.getElementById('main-cities-count').textContent = `${data.cities_visited}/${data.total_cities}`;
            document.getElementById('cities-visited').textContent = `${data.cities_visited}/${data.total_cities}`;
            
            // Check if all cities are visited and switch to mystery music
            if (data.cities_visited >= 5) {
                switchToMysteryMusic();
            }
            
            // Close the modal
            closeRiddleModal();
            
            // Show success message
            showMessage(data.message, 'success');
            
            // Update companions list if provided
            if (data.companions) {
                updateCompanions(data.companions);
            }
            
            // Check for mysterious location reveal
            if (data.mysterious_location_revealed && data.mysterious_location) {
                const iframe = document.querySelector('iframe');
                if (iframe) {
                    iframe.contentWindow.postMessage({
                        type: 'revealMysteriousLocation',
                        location: data.mysterious_location
                    }, '*');
                }
            }
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('An error occurred while submitting your answer', 'error');
    });
}

// Update the event listeners for riddle handling
document.getElementById('riddleAnswer').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault(); // Prevent form submission
        handleRiddleSubmit();
    }
});

document.querySelector('.riddle-section button').addEventListener('click', function(e) {
    e.preventDefault();
    handleRiddleSubmit();
});

// Close modal when clicking outside
document.getElementById('modalOverlay').addEventListener('click', function(e) {
    if (e.target === this) {
        closeRiddleModal();
    }
});

function closeRiddleModal() {
    const modal = document.getElementById('riddleSection');
    const overlay = document.getElementById('modalOverlay');
    const input = document.getElementById('riddleAnswer');
    
    // Clear the input
    input.value = '';
    
    // Hide both the modal and overlay
    modal.style.display = 'none';
    overlay.style.display = 'none';
    
    // Re-enable movement
    canMove = true;
    document.querySelector('.controls').classList.remove('disabled');
}

function submitRiddleAnswer() {
    handleRiddleSubmit();
}

// Add message display function if not already present
function showMessage(message, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `flash-message ${type}`;
    messageDiv.textContent = message;
    
    // Insert at the top of game-info
    const gameInfo = document.querySelector('.game-info');
    gameInfo.insertBefore(messageDiv, gameInfo.firstChild);
    
    // Remove after 5 seconds
    setTimeout(() => messageDiv.remove(), 5000);
}

// Add follower update function if not already present
function updateCompanions(companions) {
    const companionsList = document.getElementById('companions-list');
    if (companions && companions.length > 0) {
        companionsList.innerHTML = companions
            .map(companion => `<div class="companion">${companion}</div>`)
            .join('');
        
        // Update the map with companion markers
        const iframe = document.querySelector('iframe');
        if (iframe) {
            iframe.contentWindow.postMessage({
                type: 'updateCompanions',
                companions: companions
            }, '*');
        }
    } else {
        companionsList.innerHTML = '<p>No companions yet</p>';
    }
}

// Update music control functionality
const bgMusic = document.getElementById('bgMusic');
const mysteryMusic = document.getElementById('mysteryMusic');
const volumeControl = document.getElementById('volumeControl');
const volumeDisplay = document.getElementById('volumeDisplay');

// Initialize music settings
bgMusic.volume = 0.5;  // Set initial volume to 50%
mysteryMusic.volume = 0.5;  // Set initial volume to 50%

// Start background music immediately
bgMusic.play().catch(e => {
    // If autoplay is blocked, start on first interaction
    document.addEventListener('click', function startMusic() {
        bgMusic.play();
        document.removeEventListener('click', startMusic);
    }, { once: true });
});

// Handle volume changes for both audio elements
volumeControl.addEventListener('input', (e) => {
    const volume = e.target.value / 100;
    bgMusic.volume = volume;
    mysteryMusic.volume = volume;
    volumeDisplay.textContent = `${e.target.value}%`;
});

// Function to switch to mystery music
function switchToMysteryMusic() {
    const currentVolume = bgMusic.volume;
    const fadeInterval = setInterval(() => {
        if (bgMusic.volume > 0.1) {
            bgMusic.volume -= 0.1;
        } else {
            bgMusic.pause();
            mysteryMusic.volume = 0;
            mysteryMusic.play();
            let mysteryVolume = 0;
            const fadeInInterval = setInterval(() => {
                if (mysteryVolume < currentVolume) {
                    mysteryVolume += 0.1;
                    mysteryMusic.volume = mysteryVolume;
                } else {
                    clearInterval(fadeInInterval);
                }
            }, 100);
            clearInterval(fadeInterval);
        }
    }, 100);
}
