# OTP Forwarder Bot for IVASMS

A Telegram bot that automatically monitors IVASMS.com for new OTP SMS messages and forwards them to admin Telegram chats. Built with Python, Playwright for web automation, and aiogram for Telegram integration.

## Features

- 🔐 **Automatic Login**: Logs into IVASMS.com with stored credentials
- 📱 **SMS Monitoring**: Continuously watches for new OTP messages
- 📨 **Telegram Integration**: Forwards new messages to admin chats
- 📊 **History Fetching**: Retrieve historical SMS messages by date range
- 🛡️ **Admin Controls**: Secure admin-only commands for bot management
- 🔄 **Auto-restart**: Handles failures and restarts automatically
- 📝 **Comprehensive Logging**: Detailed logs for debugging and monitoring
- 🐳 **Docker Support**: Ready for GitHub Codespaces and containerized deployment

## Quick Start

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- IVASMS.com account credentials
- GitHub Codespace or Docker environment

### 1. Clone and Setup

```bash
git clone <repository-url>
cd otp-forwarder-bot
```

### 2. Environment Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Telegram Bot Configuration
TELEGRAM_TOKEN=your_telegram_bot_token_here
ADMIN_IDS=123456789,987654321

# IVASMS Credentials
IVASMS_EMAIL=your_email@domain.com
IVASMS_PASSWORD=your_password_here

# Bot Configuration
POLL_INTERVAL=8
HEADLESS=true
LOG_LEVEL=INFO
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install --with-deps
```

### 4. Run the Bot

```bash
python run.py
```

Or use the startup script:

```bash
./run.sh
```

## GitHub Codespaces Setup

### 1. Open in Codespace

1. Fork this repository
2. Click "Code" → "Codespaces" → "Create codespace"
3. Wait for the container to build

### 2. Configure Secrets

In your GitHub repository, go to Settings → Secrets and variables → Actions, and add:

- `TELEGRAM_TOKEN`: Your Telegram bot token
- `IVASMS_EMAIL`: Your IVASMS email
- `IVASMS_PASSWORD`: Your IVASMS password

### 3. Update Environment

The bot will automatically use GitHub secrets in Codespaces. No additional configuration needed.

### 4. Run the Bot

```bash
python run.py
```

## Docker Deployment

### Build and Run

```bash
# Build the image
docker build -t otp-forwarder-bot .

# Run the container
docker run -d \
  --name otp-bot \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  otp-forwarder-bot
```

### Docker Compose

```yaml
version: '3.8'
services:
  otp-bot:
    build: .
    container_name: otp-forwarder-bot
    env_file: .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

## Telegram Commands

### General Commands
- `/start` - Show bot status and info
- `/help` - Show available commands

### Admin Commands
- `/status` - Show detailed bot status
- `/config` - Show bot configuration (sanitized)
- `/recent [n]` - Show last n SMS messages (default: 10)
- `/last` - Show latest SMS message
- `/history <start> <end>` - Get SMS history for date range
- `/getotp` - Fetch current messages from page

### Owner Commands
- `/set_admin <user_id>` - Add new admin
- `/restart` - Restart the bot

### Examples
```
/history 2025-09-01 2025-09-30
/recent 5
/set_admin 987654321
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_TOKEN` | Telegram bot token | Yes | - |
| `ADMIN_IDS` | Comma-separated admin user IDs | Yes | - |
| `IVASMS_EMAIL` | IVASMS login email | Yes | - |
| `IVASMS_PASSWORD` | IVASMS login password | Yes | - |
| `POLL_INTERVAL` | Polling interval in seconds | No | 8 |
| `HEADLESS` | Run browser in headless mode | No | true |
| `LOG_LEVEL` | Logging level | No | INFO |

### Configuration File (config.yaml)

The bot uses `config.yaml` for non-sensitive configuration:

```yaml
site:
  base_url: "https://www.ivasms.com"
  login_path: "/login"
  sms_path: "/portal/sms/received"

playwright:
  timeout_ms: 30000
  retries: 3
  headless: true

telegram:
  notify_on_start: true
  notify_on_errors: true
  max_message_length: 4096

selectors:
  # CSS selectors for web elements
  # Update these if the website structure changes
```

## Architecture

```
otp-ivasms-bot/
├── src/
│   ├── bot.py              # Telegram bot implementation
│   ├── monitor.py          # Playwright automation
│   ├── storage.py          # Data persistence
│   ├── config.py           # Configuration management
│   ├── logger_setup.py     # Logging configuration
│   └── main.py             # Application entry point
├── tests/                  # Unit tests
├── logs/                   # Log files
├── Dockerfile              # Docker configuration
├── .devcontainer/          # Codespaces configuration
├── requirements.txt        # Python dependencies
├── config.yaml            # Bot configuration
├── .env.example           # Environment template
└── README.md              # This file
```

## Message Format

When a new OTP is received, the bot sends a formatted message:

```
🆕 New SMS received

From: +1234567890
Message: Your code is 123456
Time: 2025-01-01 12:00:00
URL: https://www.ivasms.com/portal/sms/received
```

## Error Handling

The bot includes comprehensive error handling:

- **Login Failures**: Automatic retry with exponential backoff
- **Popup Handling**: Graceful handling of onboarding popups
- **Network Issues**: Automatic reconnection and session recovery
- **CAPTCHA Detection**: Pauses and notifies admins
- **Browser Crashes**: Automatic restart and recovery

## Logging

Logs are stored in the `logs/` directory:

- `bot.log` - Main application log with rotation
- Console output for real-time monitoring
- Structured logging with timestamps and levels

## Security

- Credentials stored in environment variables only
- Admin-only commands protected by user ID verification
- No sensitive data in logs or Telegram messages
- Secure credential handling throughout the application

## Troubleshooting

### Common Issues

1. **Login Failed**
   - Check credentials in `.env`
   - Verify IVASMS account is active
   - Check for CAPTCHA requirements

2. **Bot Not Responding**
   - Check Telegram bot token
   - Verify admin IDs are correct
   - Check logs for errors

3. **No SMS Detected**
   - Verify selectors in `config.yaml`
   - Check if page structure changed
   - Enable debug logging

### Debug Mode

Set `LOG_LEVEL=DEBUG` in `.env` for detailed logging:

```env
LOG_LEVEL=DEBUG
```

### Screenshots

The bot can take screenshots on errors for debugging. Check the logs directory for `error_screenshot_*.png` files.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
pylint src/

# Type checking
mypy src/
```

### Adding New Features

1. Create feature branch
2. Implement changes
3. Add tests
4. Update documentation
5. Submit pull request

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This bot is for educational and personal use only. Ensure you have permission to scrape the target website and comply with their terms of service. The website owner has explicitly allowed scraping for this use case.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the logs
3. Open an issue on GitHub
4. Contact the maintainers

---

**Note**: This bot requires a valid IVASMS.com account and Telegram bot token. Make sure to keep your credentials secure and never commit them to version control.
