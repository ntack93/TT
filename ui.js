// Global triggers array
let triggers = [];

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set initial checkbox and input values from localStorage
    const rememberUsername = localStorage.getItem('rememberUsername') === 'true';
    const rememberPassword = localStorage.getItem('rememberPassword') === 'true';
    document.getElementById('rememberUsername').checked = rememberUsername;
    document.getElementById('rememberPassword').checked = rememberPassword;

    if (rememberUsername) {
        document.getElementById('usernameInput').value = localStorage.getItem('username') || '';
    }
    if (rememberPassword) {
        document.getElementById('passwordInput').value = localStorage.getItem('password') || '';
    }

    // Load and set the state of the Google Places API key
    const googlePlacesApiKey = localStorage.getItem('googlePlacesApiKey') || '';
    document.getElementById('googlePlacesApiKey').value = googlePlacesApiKey;

    // Load and set the state of the Logon Automation checkbox
    const logonAutomation = localStorage.getItem('logonAutomation') === 'true';
    document.getElementById('logonAutomation').checked = logonAutomation;

    // Load and set the state of the Auto Login checkbox
    const autoLogin = localStorage.getItem('autoLogin') === 'true';
    document.getElementById('autoLogin').checked = autoLogin;

    // Load and set the state of the Giphy API key
    const giphyApiKey = localStorage.getItem('giphyApiKey') || '';
    document.getElementById('giphyApiKey').value = giphyApiKey;

    // Load and set the state of the Keep Alive checkbox
    const keepAlive = localStorage.getItem('keepAlive') === 'true';
    document.getElementById('keepAliveCheckbox').checked = keepAlive;

    // Add event listener for the "Split View" button
    document.getElementById('splitViewButton').addEventListener('click', splitView);

    // Add event listener for the "Teleconference" button
    document.getElementById('teleconferenceButton').addEventListener('click', startTeleconference);

    // Add context menus to input fields
    addContextMenu(document.getElementById('hostInput'));
    addContextMenu(document.getElementById('usernameInput'));
    addContextMenu(document.getElementById('passwordInput'));
    addContextMenu(document.getElementById('inputBox'));
    addContextMenu(document.getElementById('googlePlacesApiKey'));
    addContextMenu(document.getElementById('giphyApiKey'));

    // Favorites and Settings window event handlers
    document.getElementById('favoritesButton').addEventListener('click', toggleFavoritesWindow);
    document.getElementById('closeFavoritesButton').addEventListener('click', toggleFavoritesWindow);
    document.getElementById('addFavoriteButton').addEventListener('click', addFavorite);
    document.getElementById('removeFavoriteButton').addEventListener('click', removeFavorite);

    document.getElementById('saveSettingsButton').addEventListener('click', saveSettings);

    // Attach the keydown listener to the inputBox after DOM loads
    const inputBox = document.getElementById('inputBox');
    inputBox.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent default behavior (e.g., form submission)
            
            // Get the current value (without trimming here if you want to allow spaces)
            const text = inputBox.value;

            if (text.trim() === "") {
                // If the input is empty (or only spaces), send an ENTER keystroke
                sendMessage('enter');
            } else {
                // Otherwise, send the typed message normally
                sendMessage('message');
            }
            // Clear the input field after sending
            inputBox.value = "";
        }
    });

    // Initialize the trigger system
    loadTriggers();
    document.getElementById('addTriggerButton').addEventListener('click', addTriggerRow);

    // Add event listener for the "Triggers" button in the main UI
    document.getElementById('triggersButton').addEventListener('click', function() {
        document.getElementById('triggersWindow').style.display = 'block';
        loadTriggersIntoUI();
    });

    // Add event listener for the "Save" button in the triggers window
    document.getElementById('saveTriggersButton').addEventListener('click', function() {
        saveTriggersFromUI();
        alert('Triggers saved!');
    });

    // Add event listener for the "Close" button in the triggers window
    document.getElementById('closeTriggersButton').addEventListener('click', function() {
        document.getElementById('triggersWindow').style.display = 'none';
    });

    // Add event listener for the "Clear" button in the chatlog window
    document.getElementById('clearChatlogButton').addEventListener('click', clearActiveChatlog);

    // Initialize the members list
    updateMembersDisplay();
});

// Save settings when the "Save" button is clicked in the settings window
function saveSettings() {
    // Save the Google Places API key
    const googlePlacesApiKey = document.getElementById('googlePlacesApiKey').value;
    localStorage.setItem('googlePlacesApiKey', googlePlacesApiKey);

    // Save the state of the Logon Automation checkbox
    const logonAutomation = document.getElementById('logonAutomation').checked;
    localStorage.setItem('logonAutomation', logonAutomation);

    // Save the state of the Auto Login checkbox
    const autoLogin = document.getElementById('autoLogin').checked;
    localStorage.setItem('autoLogin', autoLogin);

    // Save the Giphy API key
    const giphyApiKey = document.getElementById('giphyApiKey').value;
    localStorage.setItem('giphyApiKey', giphyApiKey);

    // Save the state of the Keep Alive checkbox
    const keepAlive = document.getElementById('keepAliveCheckbox').checked;
    localStorage.setItem('keepAlive', keepAlive);

    // (You can add additional settings saving logic here)

    alert('Settings saved!');
}

// Split View functionality: clones the main container and appends it
function splitView() {
    const mainContainer = document.getElementById('mainContainer');
    const clone = mainContainer.cloneNode(true);
    mainContainer.parentNode.appendChild(clone);
    console.log("Split View button clicked");
}

// Teleconference functionality: sends a specific command
function startTeleconference() {
    sendMessage('/go tele');
    console.log("Teleconference button clicked");
}

// Example sendMessage function to handle different types of commands/messages
function sendMessage(typeOrCommand) {
    const inputBox = document.getElementById('inputBox');
    const message = inputBox.value; // already cleared by the caller if needed

    if (typeOrCommand === 'enter') {
        console.log('Sending ENTER keystroke to BBS');
        // Here, implement your AJAX/WebSocket call to send a newline (e.g., '\r\n')
    } else if (typeOrCommand === 'message') {
        console.log(`Sending message: ${message}`);
        // Here, send the actual text message (append newline as needed)
    } else {
        // Handle any other command types if necessary
        console.log(`Sending command: ${typeOrCommand}`);
    }

    // Clear the field (redundant if already cleared above)
    inputBox.value = "";
}

// Add event listener for the input box to handle Enter key press
document.getElementById('inputBox').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        sendMessage('message');
        event.preventDefault(); // Prevent the default action to avoid form submission
    }
});

// Context Menu implementation for input fields
function addContextMenu(inputElement) {
    inputElement.addEventListener('contextmenu', function(event) {
        event.preventDefault();
        const contextMenu = document.createElement('div');
        contextMenu.className = 'context-menu';
        contextMenu.style.top = `${event.clientY}px`;
        contextMenu.style.left = `${event.clientX}px`;

        const cutOption = document.createElement('div');
        cutOption.textContent = 'Cut';
        cutOption.addEventListener('click', function() {
            document.execCommand('cut');
            document.body.removeChild(contextMenu);
        });
        contextMenu.appendChild(cutOption);

        const copyOption = document.createElement('div');
        copyOption.textContent = 'Copy';
        copyOption.addEventListener('click', function() {
            document.execCommand('copy');
            document.body.removeChild(contextMenu);
        });
        contextMenu.appendChild(copyOption);

        const pasteOption = document.createElement('div');
        pasteOption.textContent = 'Paste';
        pasteOption.addEventListener('click', function() {
            document.execCommand('paste');
            document.body.removeChild(contextMenu);
        });
        contextMenu.appendChild(pasteOption);

        const selectAllOption = document.createElement('div');
        selectAllOption.textContent = 'Select All';
        selectAllOption.addEventListener('click', function() {
            document.execCommand('selectAll');
            document.body.removeChild(contextMenu);
        });
        contextMenu.appendChild(selectAllOption);

        document.body.appendChild(contextMenu);

        // Remove the context menu when clicking elsewhere
        document.addEventListener('click', function() {
            if (contextMenu) {
                if (document.body.contains(contextMenu)) {
                    document.body.removeChild(contextMenu);
                }
            }
        }, { once: true });
    });
}

// Favorites window toggle
function toggleFavoritesWindow() {
    const favWindow = document.getElementById('favoritesWindow');
    if (favWindow.style.display === 'none' || favWindow.style.display === '') {
        favWindow.style.display = 'block';
        loadFavorites();
    } else {
        favWindow.style.display = 'none';
    }
}

// Load favorites from localStorage and populate the list
function loadFavorites() {
    const favoritesList = document.getElementById('favoritesList');
    favoritesList.innerHTML = '';
    const favorites = JSON.parse(localStorage.getItem('favorites')) || [];
    favorites.forEach(address => {
        const li = document.createElement('li');
        li.textContent = address;
        li.addEventListener('click', function() {
            // When a favorite is clicked, set the host input field
            document.getElementById('hostInput').value = address;
            // Mark as selected
            const lis = favoritesList.getElementsByTagName('li');
            for (let item of lis) {
                item.classList.remove('selected');
            }
            li.classList.add('selected');
        });
        favoritesList.appendChild(li);
    });
}

// Add a new favorite address
function addFavorite() {
    const newFav = document.getElementById('newFavoriteInput').value.trim();
    if (!newFav) return;
    const favorites = JSON.parse(localStorage.getItem('favorites')) || [];
    if (!favorites.includes(newFav)) {
        favorites.push(newFav);
        localStorage.setItem('favorites', JSON.stringify(favorites));
        loadFavorites();
        document.getElementById('newFavoriteInput').value = '';
    }
}

// Remove the selected favorite address
function removeFavorite() {
    const favoritesList = document.getElementById('favoritesList');
    const selected = favoritesList.querySelector('li.selected');
    if (selected) {
        let favorites = JSON.parse(localStorage.getItem('favorites')) || [];
        favorites = favorites.filter(address => address !== selected.textContent);
        localStorage.setItem('favorites', JSON.stringify(favorites));
        loadFavorites();
    }
}

// --- Trigger System Functions ---

// Load triggers from localStorage
function loadTriggers() {
    const stored = localStorage.getItem('triggers');
    if (stored) {
        triggers = JSON.parse(stored);
    } else {
        triggers = [];
    }
    renderTriggerList();
}

// Save triggers to localStorage
function saveTriggers() {
    localStorage.setItem('triggers', JSON.stringify(triggers));
}

// Render the trigger rows in the trigger list container
function renderTriggerList() {
    const container = document.getElementById('triggerList');
    container.innerHTML = "";
    triggers.forEach((trigger, index) => {
        const row = document.createElement('div');
        row.className = 'triggerRow';
        row.style.marginBottom = '5px';

        // Input for trigger text
        const triggerInput = document.createElement('input');
        triggerInput.type = 'text';
        triggerInput.placeholder = 'Trigger Text';
        triggerInput.value = trigger.trigger;
        triggerInput.style.marginRight = '5px';
        triggerInput.addEventListener('input', function() {
            triggers[index].trigger = triggerInput.value;
            saveTriggers();
        });
        row.appendChild(triggerInput);

        // Input for response text
        const responseInput = document.createElement('input');
        responseInput.type = 'text';
        responseInput.placeholder = 'Response Text';
        responseInput.value = trigger.response;
        responseInput.style.marginRight = '5px';
        responseInput.addEventListener('input', function() {
            triggers[index].response = responseInput.value;
            saveTriggers();
        });
        row.appendChild(responseInput);

        // Remove button
        const removeBtn = document.createElement('button');
        removeBtn.textContent = 'Remove';
        removeBtn.addEventListener('click', function() {
            triggers.splice(index, 1);
            saveTriggers();
            renderTriggerList();
        });
        row.appendChild(removeBtn);

        container.appendChild(row);
    });
}

// Add a new trigger row (up to 10)
function addTriggerRow() {
    if (triggers.length >= 10) {
        alert("You can only add up to 10 triggers.");
        return;
    }
    // Push an empty trigger/response object
    triggers.push({ trigger: "", response: "" });
    saveTriggers();
    renderTriggerList();
}

// Check incoming messages for triggers and send automated response if matched
function checkTriggers(message) {
    // Loop through the triggers array
    triggers.forEach(triggerObj => {
        // Perform a case-insensitive check if the trigger text exists in the message
        if (triggerObj.trigger && message.toLowerCase().includes(triggerObj.trigger.toLowerCase())) {
            // Send the associated response
            sendCustomMessage(triggerObj.response);
        }
    });
}

// Example function to send a custom message (for trigger responses)
function sendCustomMessage(message) {
    console.log("Sending custom message: " + message);
    // Implement your AJAX or WebSocket call to the backend as needed.
    // For example, you might call:
    // yourBackend.sendMessage(message + "\r\n");
}

// Load stored triggers from localStorage into the 10 rows of the triggers table.
function loadTriggersIntoUI() {
    let stored = localStorage.getItem('triggers');
    let triggersData = stored ? JSON.parse(stored) : [];
    
    // Ensure we have exactly 10 rows
    while (triggersData.length < 10) {
        triggersData.push({ trigger: "", response: "" });
    }
    if (triggersData.length > 10) {
        triggersData = triggersData.slice(0, 10);
    }
    
    // Populate the table rows
    const rows = document.querySelectorAll('#triggersTable tbody tr');
    rows.forEach((row, index) => {
        const triggerInput = row.querySelector('.triggerInput');
        const responseInput = row.querySelector('.responseInput');
        triggerInput.value = triggersData[index].trigger;
        responseInput.value = triggersData[index].response;
    });
}

// Gather the values from the 10 rows and save them as the triggers array in localStorage.
function saveTriggersFromUI() {
    const rows = document.querySelectorAll('#triggersTable tbody tr');
    const newTriggers = [];
    rows.forEach(row => {
        const triggerInput = row.querySelector('.triggerInput');
        const responseInput = row.querySelector('.responseInput');
        newTriggers.push({
            trigger: triggerInput.value.trim(),
            response: responseInput.value.trim()
        });
    });
    localStorage.setItem('triggers', JSON.stringify(newTriggers));
}

// Clear chatlog messages for the currently selected user in the listbox
function clearActiveChatlog() {
    const chatlogList = document.getElementById('chatlogList');
    const selected = chatlogList.querySelector('li.selected');
    if (selected) {
        const username = selected.textContent;
        clearChatlogForUser(username);
        displayChatlogMessages(null);  // Refresh the display
    }
}

// Clear all chatlog messages for the specified username
function clearChatlogForUser(username) {
    let chatlog = JSON.parse(localStorage.getItem('chatlog')) || {};
    if (username in chatlog) {
        chatlog[username] = [];  // Reset the messages list
        localStorage.setItem('chatlog', JSON.stringify(chatlog));
    }
}

// Display messages for the selected user
function displayChatlogMessages(event) {
    const chatlogList = document.getElementById('chatlogList');
    const selected = chatlogList.querySelector('li.selected');
    if (selected) {
        const username = selected.textContent;
        let chatlog = JSON.parse(localStorage.getItem('chatlog')) || {};
        const messages = chatlog[username] || [];
        const chatlogDisplay = document.getElementById('chatlogDisplay');
        chatlogDisplay.innerHTML = messages.map(msg => `<p>${msg}</p>`).join('');
    }
}

// Update the chat members Listbox with the current chat_members set
function updateMembersDisplay() {
    const membersList = document.getElementById('membersList');
    membersList.innerHTML = '';
    const chatMembers = JSON.parse(localStorage.getItem('chatMembers')) || [];
    chatMembers.forEach(member => {
        const li = document.createElement('li');
        li.textContent = member;
        membersList.appendChild(li);
    });
}

// Example function to update chat members (this should be called whenever chat members change)
function updateChatMembers(newMembers) {
    localStorage.setItem('chatMembers', JSON.stringify(newMembers));
    updateMembersDisplay();
}

// Example function to simulate receiving chatroom data and updating members
function simulateChatroomData() {
    const chatroomData = `
        You are in the MajorLink channel.
        Topic: (General Chat).
        BlaZ@thepenaltybox.org, Chatbot@thepenaltybox.org, Hornet@thepenaltybox.org,
        Khan@sos-bbs.net, Living.Fart@sos-bbs.net, Matlock@thepenaltybox.org,
        NerdTower@ccxbbs.net, Night@thepenaltybox.org, and Nodin@thepenaltybox.org are
        here with you.
        Just press "?" if you need any assistance.
    `;
    const lines = chatroomData.split('\n');
    const members = extractUsernamesFromLines(lines);
    updateChatMembers(members);
}

// Extract usernames from chatroom lines
function extractUsernamesFromLines(lines) {
    const combined = lines.join(' ');
    const match = combined.match(/([\w@.\-]+(?:, [\w@.\-]+)*, and [\w@.\-]+) are here with you\./);
    if (match) {
        const usernamesStr = match[1];
        return usernamesStr.split(/,\s*|\s*and\s*/);
    }
    return [];
}

// Call simulateChatroomData to test the functionality
simulateChatroomData();
