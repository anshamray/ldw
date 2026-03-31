const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const config = require('../config');

let messages = {
    meta: {
        created: new Date().toISOString(),
        lastUpdated: new Date().toISOString(),
        totalSubmitted: 0,
        totalFiltered: 0
    },
    queue: []
};

// Default phrases to show when queue is empty
let defaultPhrases = [
    'Willkommen zur Langen Nacht der Wissenschaft!'
];

function loadDefaultPhrases() {
    const filePath = path.resolve(config.DEFAULT_PHRASES_FILE);

    if (fs.existsSync(filePath)) {
        try {
            const content = fs.readFileSync(filePath, 'utf8');
            const phrases = content
                .split('\n')
                .map(p => p.trim())
                .filter(p => p.length > 0);

            if (phrases.length > 0) {
                defaultPhrases = phrases;
                console.log(`Loaded ${phrases.length} default phrases`);
            }
        } catch (err) {
            console.error('Error loading default phrases:', err);
        }
    }
}

function getRandomDefaultPhrase() {
    const index = Math.floor(Math.random() * defaultPhrases.length);
    return defaultPhrases[index];
}

function ensureDataDir() {
    const dataDir = path.resolve(config.DATA_DIR);
    if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
    }
}

function loadMessages() {
    ensureDataDir();
    const filePath = path.resolve(config.MESSAGES_FILE);

    if (fs.existsSync(filePath)) {
        try {
            const data = fs.readFileSync(filePath, 'utf8');
            messages = JSON.parse(data);
            console.log(`Loaded ${messages.queue.length} messages from storage`);
        } catch (err) {
            console.error('Error loading messages:', err);
        }
    }
}

function saveMessages() {
    ensureDataDir();
    const filePath = path.resolve(config.MESSAGES_FILE);
    const tempPath = filePath + '.tmp';

    messages.meta.lastUpdated = new Date().toISOString();

    try {
        fs.writeFileSync(tempPath, JSON.stringify(messages, null, 2));
        fs.renameSync(tempPath, filePath);
    } catch (err) {
        console.error('Error saving messages:', err);
    }
}

function addMessage(text) {
    const id = `msg_${Date.now()}_${uuidv4().slice(0, 8)}`;
    const message = {
        id,
        text,
        submittedAt: new Date().toISOString(),
        status: 'pending',
        displayedAt: null,
        displayedBy: null
    };

    messages.queue.push(message);
    messages.meta.totalSubmitted++;
    saveMessages();

    const position = messages.queue.filter(m => m.status === 'pending').length;

    return { id, position };
}

function incrementFiltered() {
    messages.meta.totalFiltered++;
    saveMessages();
}

function getNextMessage(displayId) {
    const now = Date.now();

    // Only return messages that have been in queue for at least MESSAGE_DELAY_MS
    // This gives admins time to review and delete inappropriate messages
    const pending = messages.queue.find(m => {
        if (m.status !== 'pending') return false;

        const submittedTime = new Date(m.submittedAt).getTime();
        const age = now - submittedTime;

        return age >= config.MESSAGE_DELAY_MS;
    });

    if (pending) {
        return pending;
    }

    // No pending messages - return a default phrase
    return {
        id: `default_${Date.now()}`,
        text: getRandomDefaultPhrase(),
        isDefault: true
    };
}

function markDisplayed(messageId, displayId) {
    // Default phrases don't need to be marked as displayed
    if (messageId.startsWith('default_')) {
        return { success: true, nextMessageAvailable: true };
    }

    const message = messages.queue.find(m => m.id === messageId);

    if (!message) {
        return { success: false, error: 'Message not found' };
    }

    message.status = 'displayed';
    message.displayedAt = new Date().toISOString();
    message.displayedBy = displayId;
    saveMessages();

    const hasNext = messages.queue.some(m => m.status === 'pending');

    return { success: true, nextMessageAvailable: hasNext };
}

function getQueueStatus() {
    const pending = messages.queue.filter(m => m.status === 'pending').length;
    const displayed = messages.queue.filter(m => m.status === 'displayed').length;
    const displays = [...new Set(
        messages.queue
            .filter(m => m.displayedBy)
            .map(m => m.displayedBy)
    )];

    return {
        totalMessages: messages.queue.length,
        pendingMessages: pending,
        displayedMessages: displayed,
        activeDisplays: displays,
        totalFiltered: messages.meta.totalFiltered
    };
}

function getAllMessages() {
    const now = Date.now();

    return messages.queue.map(m => {
        const submittedTime = new Date(m.submittedAt).getTime();
        const age = now - submittedTime;
        const readyIn = Math.max(0, config.MESSAGE_DELAY_MS - age);

        return {
            ...m,
            queuePosition: m.status === 'pending'
                ? messages.queue.filter(msg => msg.status === 'pending' && msg.submittedAt <= m.submittedAt).length
                : null,
            // Time remaining before message can be shown (0 = ready)
            readyInMs: m.status === 'pending' ? readyIn : null,
            isReady: m.status === 'pending' ? readyIn === 0 : null
        };
    });
}

function deleteMessage(messageId) {
    const index = messages.queue.findIndex(m => m.id === messageId);

    if (index === -1) {
        return { success: false, error: 'Message not found' };
    }

    messages.queue.splice(index, 1);
    saveMessages();

    return { success: true };
}

function clearDisplayed() {
    const beforeCount = messages.queue.length;
    messages.queue = messages.queue.filter(m => m.status === 'pending');
    saveMessages();

    return { success: true, removed: beforeCount - messages.queue.length };
}

// Load messages and default phrases on startup
loadMessages();
loadDefaultPhrases();

module.exports = {
    addMessage,
    incrementFiltered,
    getNextMessage,
    markDisplayed,
    getQueueStatus,
    getAllMessages,
    deleteMessage,
    clearDisplayed
};
