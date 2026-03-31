const express = require('express');
const crypto = require('crypto');
const router = express.Router();
const messageService = require('../services/messageService');
const config = require('../config');

// Simple session store (in-memory)
const sessions = new Set();

// Generate session token
function generateToken() {
    return crypto.randomBytes(32).toString('hex');
}

// Auth middleware
function requireAuth(req, res, next) {
    const token = req.headers.authorization?.replace('Bearer ', '');

    if (!token || !sessions.has(token)) {
        return res.status(401).json({ error: 'Unauthorized' });
    }

    next();
}

// POST /api/v1/admin/login - Login with password
router.post('/login', (req, res) => {
    const { password } = req.body;

    if (password === config.ADMIN_PASSWORD) {
        const token = generateToken();
        sessions.add(token);

        // Clean up old sessions after 24 hours
        setTimeout(() => sessions.delete(token), 24 * 60 * 60 * 1000);

        res.json({ success: true, token });
    } else {
        res.status(401).json({ success: false, error: 'Invalid password' });
    }
});

// POST /api/v1/admin/logout - Logout
router.post('/logout', (req, res) => {
    const token = req.headers.authorization?.replace('Bearer ', '');
    if (token) {
        sessions.delete(token);
    }
    res.json({ success: true });
});

// GET /api/v1/admin/messages - Get all messages for moderation
router.get('/messages', requireAuth, (req, res) => {
    const messages = messageService.getAllMessages();
    const status = messageService.getQueueStatus();

    res.json({
        status,
        messages
    });
});

// DELETE /api/v1/admin/messages/:messageId - Delete a message
router.delete('/messages/:messageId', requireAuth, (req, res) => {
    const { messageId } = req.params;
    const result = messageService.deleteMessage(messageId);

    if (!result.success) {
        return res.status(404).json(result);
    }

    res.json(result);
});

// POST /api/v1/admin/clear-displayed - Clear all displayed messages
router.post('/clear-displayed', requireAuth, (req, res) => {
    const result = messageService.clearDisplayed();
    res.json(result);
});

module.exports = router;
