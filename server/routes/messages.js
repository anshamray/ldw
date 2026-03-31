const express = require('express');
const router = express.Router();
const messageService = require('../services/messageService');
const filterService = require('../services/filterService');
const config = require('../config');

// Simple in-memory rate limiter per IP
const rateLimitMap = new Map();

function rateLimit(req, res, next) {
    const ip = req.ip || req.connection.remoteAddress;
    const now = Date.now();
    const windowMs = config.RATE_LIMIT_WINDOW_MS;
    const maxRequests = config.RATE_LIMIT_MAX;

    if (!rateLimitMap.has(ip)) {
        rateLimitMap.set(ip, []);
    }

    const timestamps = rateLimitMap.get(ip).filter(t => now - t < windowMs);
    rateLimitMap.set(ip, timestamps);

    if (timestamps.length >= maxRequests) {
        return res.status(429).json({
            success: false,
            error: 'RATE_LIMITED',
            message: 'Zu viele Nachrichten. Bitte warten Sie einen Moment.'
        });
    }

    timestamps.push(now);
    next();
}

// Clean up old entries periodically
setInterval(() => {
    const now = Date.now();
    for (const [ip, timestamps] of rateLimitMap) {
        const filtered = timestamps.filter(t => now - t < 60000);
        if (filtered.length === 0) {
            rateLimitMap.delete(ip);
        } else {
            rateLimitMap.set(ip, filtered);
        }
    }
}, 60000);

// POST /api/v1/messages - Submit a new message
router.post('/', rateLimit, (req, res) => {
    const { text } = req.body;

    const validation = filterService.validateMessage(text);

    if (!validation.valid) {
        messageService.incrementFiltered();
        return res.status(400).json({
            success: false,
            error: validation.reason,
            message: validation.message
        });
    }

    const result = messageService.addMessage(validation.sanitized);

    res.status(201).json({
        success: true,
        messageId: result.id,
        position: result.position
    });
});

// GET /api/v1/messages/next - Get next message for display
router.get('/next', (req, res) => {
    const displayId = req.query.displayId || 'unknown';
    const message = messageService.getNextMessage(displayId);

    if (!message) {
        return res.status(204).send();
    }

    res.json({
        messageId: message.id,
        text: message.text,
        displayedAt: message.displayedAt,
        queuePosition: message.isDefault ? null : 1,
        isDefault: message.isDefault || false
    });
});

// POST /api/v1/messages/:messageId/displayed - Mark message as displayed
router.post('/:messageId/displayed', (req, res) => {
    const { messageId } = req.params;
    const { displayId } = req.body;

    const result = messageService.markDisplayed(messageId, displayId || 'unknown');

    if (!result.success) {
        return res.status(404).json({
            success: false,
            error: result.error
        });
    }

    res.json({
        success: true,
        nextMessageAvailable: result.nextMessageAvailable
    });
});

module.exports = router;
