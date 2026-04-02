# Raspberry Pi LED Display Client Configuration

# Server URL - set to the IP/hostname of your message server
# Examples:
#   Local network: "http://192.168.1.100:3000"
#   VPS:           "https://ldw.example.com"
SERVER_URL = "http://172.16.155.51:3000"

# Unique identifier for this display
DISPLAY_ID = "pi-01"

# How long to show each message (seconds) - for short text that fits on screen
DISPLAY_TIME = 10

# After scrolling long text, pause this many seconds so viewers can read the end
SCROLL_END_PAUSE = 3

# Polling interval when queue is empty (seconds)
POLL_INTERVAL = 2
