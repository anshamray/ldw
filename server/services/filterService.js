const fs = require('fs');
const path = require('path');
const Filter = require('bad-words');
const config = require('../config');

const filter = new Filter();

// Banned phrases (case insensitive)
const bannedPhrases = [
    'from the river to the sea',
    'vom fluss bis zum meer'
];

// Load word list from file
function loadWordList(filename) {
    const wordlistPath = path.resolve(config.WORDLIST_DIR, filename);

    if (fs.existsSync(wordlistPath)) {
        try {
            const content = fs.readFileSync(wordlistPath, 'utf8');
            const words = content
                .split('\n')
                .map(w => w.trim().toLowerCase())
                .filter(w => w.length > 0);

            filter.addWords(...words);
            console.log(`Loaded ${words.length} words from ${filename}`);
        } catch (err) {
            console.error(`Error loading wordlist ${filename}:`, err);
        }
    }
}

// Load both German and English word lists
loadWordList('german.txt');
loadWordList('english.txt');

// Check for banned phrases (case insensitive)
function containsBannedPhrase(text) {
    const lowerText = text.toLowerCase();
    return bannedPhrases.some(phrase => lowerText.includes(phrase));
}

function validateMessage(text) {
    // Check if text exists
    if (!text || typeof text !== 'string') {
        return {
            valid: false,
            reason: 'EMPTY_MESSAGE',
            message: 'Text ist erforderlich.'
        };
    }

    const trimmed = text.trim();

    // Check empty after trim
    if (trimmed.length === 0) {
        return {
            valid: false,
            reason: 'EMPTY_MESSAGE',
            message: 'Text ist erforderlich.'
        };
    }

    // Check max length
    if (trimmed.length > config.MAX_MESSAGE_LENGTH) {
        return {
            valid: false,
            reason: 'TOO_LONG',
            message: `Text ist zu lang (max ${config.MAX_MESSAGE_LENGTH} Zeichen).`
        };
    }

    // Block URLs and emails
    if (/https?:\/\/|www\.|@\w+\.\w+/i.test(trimmed)) {
        return {
            valid: false,
            reason: 'CONTAINS_URL',
            message: 'URLs und E-Mail-Adressen sind nicht erlaubt.'
        };
    }

    // Check banned phrases (case insensitive)
    if (containsBannedPhrase(trimmed)) {
        return {
            valid: false,
            reason: 'BANNED_PHRASE',
            message: 'Die Nachricht enthält unzulässige Inhalte.'
        };
    }

    // Check profanity (case insensitive - handled by bad-words library)
    if (filter.isProfane(trimmed)) {
        return {
            valid: false,
            reason: 'PROFANITY_DETECTED',
            message: 'Die Nachricht enthält unzulässige Wörter.'
        };
    }

    // Check spam patterns (6+ repeated characters)
    if (/(.)\1{5,}/.test(trimmed)) {
        return {
            valid: false,
            reason: 'SPAM_PATTERN',
            message: 'Spam-Muster erkannt.'
        };
    }

    return {
        valid: true,
        sanitized: trimmed
    };
}

module.exports = {
    validateMessage
};
