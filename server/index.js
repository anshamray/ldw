const express = require('express');
const cors = require('cors');
const path = require('path');
const config = require('./config');
const messagesRouter = require('./routes/messages');
const adminRouter = require('./routes/admin');
const messageService = require('./services/messageService');

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Serve static frontend files
app.use(express.static(path.join(__dirname, '..')));

// API routes
app.use('/api/v1/messages', messagesRouter);
app.use('/api/v1/admin', adminRouter);

// Health check endpoint
app.get('/api/v1/health', (req, res) => {
    const status = messageService.getQueueStatus();
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        queueSize: status.pendingMessages
    });
});

// Queue status endpoint
app.get('/api/v1/queue/status', (req, res) => {
    const status = messageService.getQueueStatus();
    res.json(status);
});

// Start server
app.listen(config.PORT, () => {
    console.log(`LED Message Server running on http://localhost:${config.PORT}`);
    console.log(`API available at http://localhost:${config.PORT}/api/v1`);
    console.log('');
    console.log('Pages:');
    console.log(`  Form:  http://localhost:${config.PORT}/`);
    console.log(`  Admin: http://localhost:${config.PORT}/admin.html`);
    console.log('');
    console.log('API Endpoints:');
    console.log('  POST /api/v1/messages              - Submit message');
    console.log('  GET  /api/v1/messages/next         - Get next message (for Pi)');
    console.log('  POST /api/v1/messages/:id/displayed - Mark displayed');
    console.log('  GET  /api/v1/health                - Health check');
    console.log('  GET  /api/v1/admin/messages        - All messages (moderation)');
    console.log('  DELETE /api/v1/admin/messages/:id  - Delete message');
});
