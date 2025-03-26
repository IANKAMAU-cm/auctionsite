const socket = io.connect(window.location.origin);

let connectionStatusElement; // Declare globally
let debugLogElement; // Declare globally

// Wrap DOM-dependent code in DOMContentLoaded
document.addEventListener("DOMContentLoaded", function() {
    // Initialize connection status element
    connectionStatusElement = document.createElement('div');
    connectionStatusElement.id = 'socket-status';
    connectionStatusElement.style.position = 'fixed';
    connectionStatusElement.style.bottom = '10px';
    connectionStatusElement.style.right = '10px';
    connectionStatusElement.style.padding = '5px 10px';
    connectionStatusElement.style.borderRadius = '5px';
    connectionStatusElement.style.color = 'white';
    connectionStatusElement.style.fontSize = '12px';
    connectionStatusElement.textContent = 'Socket: Connecting...';
    connectionStatusElement.style.backgroundColor = 'orange';
    document.body.appendChild(connectionStatusElement);

    // Initialize debug log element
    debugLogElement = document.createElement('div');
    debugLogElement.id = 'debug-log';
    debugLogElement.style.position = 'fixed';
    debugLogElement.style.bottom = '70px';
    debugLogElement.style.right = '10px';
    debugLogElement.style.width = '300px';
    debugLogElement.style.height = '200px';
    debugLogElement.style.overflow = 'auto';
    debugLogElement.style.backgroundColor = 'rgba(0,0,0,0.7)';
    debugLogElement.style.color = 'white';
    debugLogElement.style.padding = '10px';
    debugLogElement.style.fontSize = '12px';
    debugLogElement.style.fontFamily = 'monospace';
    document.body.appendChild(debugLogElement);

    // Add a test button to the page
    let testButton = document.createElement('button');
    testButton.textContent = 'Test WebSocket';
    testButton.style.position = 'fixed';
    testButton.style.bottom = '40px';
    testButton.style.right = '10px';
    testButton.onclick = testSocketConnection;
    document.body.appendChild(testButton);
    
    // Add the force update button
    addForceUpdateButton();
    
    // Join auction room 
    const auctionIdElement = document.querySelector('.auction-container');
    if (auctionIdElement) {
        const auctionId = auctionIdElement.getAttribute('data-auction-id');
        if (auctionId) {
            joinAuctionRoom(auctionId);
            logDebug(`Joined auction room for auction ${auctionId}`);
        }
    }
});

socket.on('connect', () => {
    console.log('WebSocket connected successfully');
    connectionStatusElement.textContent = 'Socket: Connected';
    connectionStatusElement.style.backgroundColor = 'green';
});

socket.on('disconnect', () => {
    console.log('WebSocket disconnected');
    connectionStatusElement.textContent = 'Socket: Disconnected';
    connectionStatusElement.style.backgroundColor = 'red';
});

function logDebug(message) {
    const timestamp = new Date().toISOString().substr(11, 8);
    debugLogElement.innerHTML += `<div>[${timestamp}] ${message}</div>`;
    debugLogElement.scrollTop = debugLogElement.scrollHeight;
    console.log(`[${timestamp}] ${message}`);
}

// Join auction room with logging
function joinAuctionRoom(auctionId) {
    logDebug(`Attempting to join auction room for auction ${auctionId}`);
    socket.emit('join_auction', { auction_id: auctionId });
}

// Listen for auction updates
socket.on('auction_update', (data) => {
    console.log('Received auction_update:', data);  // Debugging
    const { auction_id, sale_status } = data;
    
    const statusElement = document.querySelector(`#auction-status-${auction_id}`);
    if (statusElement) {
        console.log(`Found status element for auction ${auction_id}`);
        statusElement.innerText = sale_status;
        if (sale_status === 'Sold') {
            statusElement.style.color = 'blue';
        } else if (sale_status === 'Open') {
            statusElement.style.color = 'green';
        } else {
            statusElement.style.color = 'red';
        }
    } else {
        console.error(`Could not find status element for auction ${auction_id}`);
    }
});

// Listen for new bids
socket.on('new_bid', (data) => {
    console.log('Received new_bid:', data);  // Debugging
    const { auction_id, bid_amount, user_id } = data;
    const bidElement = document.querySelector(`#current-bid-${auction_id}`);
    if (bidElement) {
        bidElement.textContent = `Current Bid: ${bid_amount}`;
    }
});

// Debug logging
socket.onAny((event, ...args) => {
    console.log(`Received event "${event}":`, args);
});

// Test ping-pong functionality
function testSocketConnection() {
    console.log("Sending ping_test");
    socket.emit('ping_test', {timestamp: Date.now()});
}

socket.on('pong_test', (data) => {
    console.log("Received pong_test response:", data);
    alert("WebSocket test successful: received pong response");
});

function addForceUpdateButton() {
    const button = document.createElement('button');
    button.textContent = 'Force Auction Update';
    button.style.position = 'fixed';
    button.style.bottom = '100px';
    button.style.right = '10px';
    button.style.padding = '10px';
    button.style.backgroundColor = 'blue';
    button.style.color = 'white';
    button.style.border = 'none';
    button.style.borderRadius = '5px';
    button.style.cursor = 'pointer';

    button.addEventListener('click', () => {
        const auctionIdElement = document.querySelector('.auction-container');
        if (auctionIdElement) {
            const auctionId = auctionIdElement.getAttribute('data-auction-id');
            if (auctionId) {
                fetch(`/force_auction_update/${auctionId}`, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Force update response:', data);
                    })
                    .catch(error => console.error('Error forcing update:', error));
            }
        }
    });

    document.body.appendChild(button);
}

function reloadAuctionStatus(auctionId) {
    fetch(`/auction_status/${auctionId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch auction status');
            }
            return response.text();
        })
        .then(html => {
            const container = document.getElementById('auction-status-container');
            container.innerHTML = html;

            // Reinitialize any dynamic elements (e.g., countdown timer)
            const countdown = document.getElementById('countdown');
            if (countdown) {
                const endTimeUTC = countdown.getAttribute("data-end-time");
                const endTime = new Date(endTimeUTC).getTime();

                function updateCountdown() {
                    const now = new Date().getTime();
                    const timeLeft = Math.floor((endTime - now) / 1000);

                    if (timeLeft <= 0) {
                        countdown.innerText = 'Auction Ended';
                    } else {
                        const days = Math.floor(timeLeft / (24 * 60 * 60));
                        const hours = Math.floor((timeLeft % (24 * 60 * 60)) / (60 * 60));
                        const minutes = Math.floor((timeLeft % (60 * 60)) / 60);
                        const seconds = timeLeft % 60;
                        countdown.innerText = `${days}d ${hours}h ${minutes}m ${seconds}s`;
                    }
                }

                updateCountdown();
                setInterval(updateCountdown, 1000);
            }
        })
        .catch(error => console.error('Error reloading auction status:', error));
}

// Example: Reload the auction status every 10 seconds
setInterval(() => {
    const auctionId = document.querySelector('.auction-container').getAttribute('data-auction-id');
    reloadAuctionStatus(auctionId);
}, 10000);

// Example: Reload the auction status when a WebSocket event is received
socket.on('auction_update', function(data) {
    const auctionId = document.querySelector('.auction-container').getAttribute('data-auction-id');
    if (data.auction_id == auctionId) {
        reloadAuctionStatus(auctionId);
    }
});