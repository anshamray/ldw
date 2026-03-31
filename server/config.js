module.exports = {
    PORT: process.env.PORT || 3000,
    MAX_MESSAGE_LENGTH: 200,
    DATA_DIR: './server/data',
    MESSAGES_FILE: './server/data/messages.json',
    DEFAULT_PHRASES_FILE: './server/data/default-phrases.txt',
    WORDLIST_DIR: './server/wordlists',
    ADMIN_PASSWORD: process.env.ADMIN_PASSWORD || 'AusbildungIstCool',
    // Delay before messages can be shown (in milliseconds) - gives admins time to review
    MESSAGE_DELAY_MS: 60 * 1000,  // 1 minute
    // Rate limiting: max submissions per IP within the time window
    RATE_LIMIT_MAX: parseInt(process.env.RATE_LIMIT_MAX) || 3,
    RATE_LIMIT_WINDOW_MS: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 60 * 1000  // 1 minute
};
