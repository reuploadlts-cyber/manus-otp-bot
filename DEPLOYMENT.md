# Deployment Guide

This guide covers different deployment options for the OTP Forwarder Bot.

## GitHub Codespaces (Recommended)

### 1. Fork the Repository
1. Fork this repository to your GitHub account
2. Clone your fork locally or work directly in Codespaces

### 2. Open in Codespace
1. Go to your forked repository
2. Click "Code" → "Codespaces" → "Create codespace on main"
3. Wait for the container to build (takes 2-3 minutes)

### 3. Configure Secrets
1. Go to your repository Settings
2. Navigate to "Secrets and variables" → "Actions"
3. Add the following secrets:
   - `TELEGRAM_TOKEN`: Your Telegram bot token
   - `IVASMS_EMAIL`: Your IVASMS email
   - `IVASMS_PASSWORD`: Your IVASMS password

### 4. Update Environment
The bot will automatically use GitHub secrets in Codespaces. No additional configuration needed.

### 5. Run the Bot
```bash
python run.py
```

## Docker Deployment

### 1. Build the Image
```bash
docker build -t otp-forwarder-bot .
```

### 2. Run with Environment File
```bash
docker run -d \
  --name otp-bot \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/bot_data.db:/app/bot_data.db \
  otp-forwarder-bot
```

### 3. Using Docker Compose
```bash
# Create .env file first
cp .env.example .env
# Edit .env with your credentials

# Start the bot
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the bot
docker-compose down
```

## VPS/Server Deployment

### 1. Server Requirements
- Ubuntu 20.04+ or similar Linux distribution
- Python 3.11+
- 1GB RAM minimum
- 10GB disk space
- Internet connection

### 2. Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3.11 python3.11-pip python3.11-venv -y

# Install system dependencies for Playwright
sudo apt install wget gnupg ca-certificates -y
```

### 3. Clone and Setup
```bash
# Clone repository
git clone <your-repo-url>
cd otp-forwarder-bot

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install --with-deps

# Setup environment
cp .env.example .env
# Edit .env with your credentials
```

### 4. Create Systemd Service
Create `/etc/systemd/system/otp-bot.service`:

```ini
[Unit]
Description=OTP Forwarder Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/otp-forwarder-bot
Environment=PATH=/path/to/otp-forwarder-bot/venv/bin
ExecStart=/path/to/otp-forwarder-bot/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5. Enable and Start Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable otp-bot

# Start service
sudo systemctl start otp-bot

# Check status
sudo systemctl status otp-bot

# View logs
sudo journalctl -u otp-bot -f
```

## Cloud Deployment

### AWS EC2
1. Launch an EC2 instance (t3.micro or larger)
2. Follow VPS deployment steps
3. Configure security groups for outbound HTTPS
4. Set up CloudWatch for monitoring

### Google Cloud Platform
1. Create a Compute Engine instance
2. Follow VPS deployment steps
3. Configure firewall rules
4. Set up Cloud Logging

### DigitalOcean Droplet
1. Create a droplet with Ubuntu 20.04
2. Follow VPS deployment steps
3. Configure monitoring and alerts

## Monitoring and Maintenance

### 1. Log Monitoring
```bash
# View real-time logs
tail -f logs/bot.log

# Search for errors
grep -i error logs/bot.log

# Check specific date
grep "2025-01-01" logs/bot.log
```

### 2. Health Checks
```bash
# Check if bot is running
ps aux | grep "python run.py"

# Check database
sqlite3 bot_data.db "SELECT COUNT(*) FROM sms_messages;"

# Check recent messages
sqlite3 bot_data.db "SELECT * FROM sms_messages ORDER BY received_at DESC LIMIT 5;"
```

### 3. Backup
```bash
# Backup database
cp bot_data.db backup_$(date +%Y%m%d_%H%M%S).db

# Backup logs
tar -czf logs_backup_$(date +%Y%m%d_%H%M%S).tar.gz logs/
```

### 4. Updates
```bash
# Pull latest changes
git pull origin main

# Restart service
sudo systemctl restart otp-bot

# Or if using Docker
docker-compose pull
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **Bot not starting**
   - Check .env file exists and has correct values
   - Verify Telegram token is valid
   - Check logs for specific errors

2. **Login failures**
   - Verify IVASMS credentials
   - Check if account is locked
   - Look for CAPTCHA requirements

3. **No SMS detected**
   - Check if selectors in config.yaml are correct
   - Verify page structure hasn't changed
   - Enable debug logging

4. **High memory usage**
   - Restart the bot periodically
   - Check for memory leaks in logs
   - Consider increasing server resources

### Debug Mode
Set `LOG_LEVEL=DEBUG` in .env for detailed logging:

```env
LOG_LEVEL=DEBUG
```

### Screenshots
The bot captures screenshots on errors. Check the `screenshots/` directory for debugging images.

## Security Considerations

1. **Credentials**
   - Never commit .env file
   - Use strong passwords
   - Rotate credentials regularly

2. **Access Control**
   - Limit admin IDs to trusted users
   - Use VPN for server access
   - Enable firewall rules

3. **Updates**
   - Keep dependencies updated
   - Monitor security advisories
   - Apply patches promptly

## Performance Optimization

1. **Resource Usage**
   - Monitor CPU and memory usage
   - Adjust poll interval if needed
   - Use headless mode in production

2. **Database**
   - Regular cleanup of old messages
   - Monitor database size
   - Consider archiving old data

3. **Network**
   - Use stable internet connection
   - Consider retry policies
   - Monitor network latency

## Support

For deployment issues:

1. Check the troubleshooting section
2. Review logs for errors
3. Open an issue on GitHub
4. Contact the maintainers

Remember to keep your credentials secure and never share them publicly!
