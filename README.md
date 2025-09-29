# ivasms Telegram Bot

## Project Goal

This project implements a Telegram bot designed to fetch One-Time Passwords (OTPs) from `ivasms.com`. The bot securely logs into the specified account, navigates to the "My SMS Statistics" page, scrapes incoming OTP messages, and sends new OTPs to a configured Telegram admin chat. It is built with robustness, security, and ease of deployment in mind, particularly for GitHub Codespaces environments.

## Features

*   **Secure Login & Navigation:** Logs into `ivasms.com` using provided credentials and navigates to the OTP reception page.
*   **OTP Scraping:** Continuously monitors the "My SMS Statistics" page for new OTPs, extracts relevant details (timestamp, sender, message text, service), and avoids duplicates.
*   **Telegram Notifications:** Sends real-time notifications to admin users for:
    *   Bot startup/shutdown
    *   Login success/failure
    *   Navigation success/failure to OTP section
    *   New OTPs received (with structured details)
    *   Errors and exceptions (with summary)
*   **Admin Commands:** Provides a suite of Telegram commands for administrators:
    *   `/start`: Register/start interaction; send bot status.
    *   `/status`: Return current bot status (running/stopped, last login, last OTP fetch).
    *   `/config`: Show current runtime configuration (masked sensitive data).
    *   `/info`: Show deployment info (commit SHA, branch, uptime).
    *   `/recent_otps [N]`: Show last N OTP entries (default 10).
    *   `/last_otp`: Show the most recently received OTP.
    *   `/new_otp`: Force a manual fetch and immediate send of any new OTPs.
    *   `/restart`: Safely restart the bot process.
    *   `/stop`: Stop monitoring for new OTPs.
    *   `/start_monitor`: Resume monitoring for new OTPs.
    *   `/logs [lines]`: Tail the latest log entries.
    *   `/health`: Perform a system health check.
*   **Reliability & Observability:**
    *   Uses Playwright for robust web interaction, handling JavaScript-rendered content.
    *   Robust error handling with retries and exponential backoff for network and login issues.
    *   Persists last seen OTP ID/timestamp in an SQLite database to prevent resending old OTPs after restarts.
    *   Comprehensive logging to file and console using `structlog`.
    *   Periodic heartbeat messages to confirm bot operation.
    *   Circuit breaker pattern for critical operations.
*   **Security:**
    *   Credentials and Telegram bot token are stored in environment variables, not in code.
    *   Sensitive information is masked in `/config` output.
    *   Admin commands are restricted to configured Telegram chat IDs.
*   **Development Environment:** Includes a GitHub Codespaces `devcontainer` for easy setup and development.

## Tech Stack

*   **Language:** Python 3.11+
*   **Web Scraping:** [Playwright for Python](https://playwright.dev/python/) (headless, fast, persistent browser context)
*   **Telegram Bot API:** [`python-telegram-bot`](https://python-telegram-bot.org/) (v20+) with `asyncio` support
*   **Data Storage:** [SQLite](https://www.sqlite.org/index.html) (via `sqlite-utils`) for OTP persistence and bot state.
*   **Logging:** Python's built-in `logging` module with `structlog` for structured logging and `colorama` for colored console output.
*   **Environment Management:** [`python-dotenv`](https://pypi.org/project/python-dotenv/) for local development environment variables.
*   **Development Container:** GitHub Codespaces `devcontainer` based on `mcr.microsoft.com/vscode/devcontainers/python:0-3.11`.

## Project Structure

```
ivasms-telegram-bot/
├─ .devcontainer/
│  ├─ devcontainer.json
│  └─ Dockerfile (optional, for custom images)
├─ src/
│  ├─ __init__.py
│  ├─ bot.py                 # Telegram command handlers, notifications, admin auth
│  ├─ monitor.py             # Main monitoring loop (login, navigate, fetch, process)
│  ├─ playwright_client.py    # Playwright wrapper (login, navigate, selectors, screenshot)
│  ├─ storage.py             # SQLite persistence (OTPs, bot state)
│  ├─ config.py              # Reads env vars and default config
│  ├─ logger.py              # Logging setup with structlog
│  ├─ utils.py               # Helper functions (git info, uptime, sanitization, OTP extraction)
│  ├─ error_handler.py        # Circuit breaker, retry manager, error tracker, health checker
│  └─ main.py                # Main entry point for the bot
├─ scripts/
│  ├─ start.sh               # Script to set up environment and start the bot
│  └─ run_tests.sh            # Script to run tests
├─ tests/                    # Unit and integration tests
│  ├─ conftest.py
│  ├─ test_storage.py
│  ├─ test_utils.py
│  ├─ test_bot_integration.py
│  └─ test_error_handler.py
├─ .env.example              # Example environment variables file
├─ requirements.txt          # Python dependencies
├─ .gitignore                # Git ignore file
├─ pytest.ini                # Pytest configuration
└─ README.md                # Project README
```

## Setup and Installation

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd ivasms-telegram-bot
```

### 2. Environment Variables

Copy the example environment file and fill in your details:

```bash
cp .env.example .env
```

Edit the `.env` file with your actual credentials and settings:

```ini
# ivasms Telegram Bot Configuration

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
TELEGRAM_ADMIN_CHAT_IDS=YOUR_TELEGRAM_ADMIN_CHAT_ID_1,YOUR_TELEGRAM_ADMIN_CHAT_ID_2

# ivasms.com Credentials
IVASMS_EMAIL=your_ivasms_email@example.com
IVASMS_PASSWORD=your_ivasms_password

# Bot Behavior Settings
POLL_INTERVAL_SECONDS=15
HEADLESS=true

# Storage Configuration
DB_PATH=./data/state.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=./data/bot.log

# Browser Configuration
BROWSER_TIMEOUT=30000
LOGIN_RETRY_ATTEMPTS=3
LOGIN_RETRY_DELAY=5

# Health Check Configuration
HEARTBEAT_INTERVAL_HOURS=24

# Permission Acknowledgment (REQUIRED)
# Set to 'true' to confirm you have explicit permission from the website owner.
OWNER_PERMISSION_ACKNOWLEDGED=true
PERMISSION_REFERENCE="Website owner permission granted for OTP scraping - [Link to permission document/email]"
```

**Important:** Ensure `OWNER_PERMISSION_ACKNOWLEDGED` is set to `true` and provide a `PERMISSION_REFERENCE` as evidence of consent. This is crucial for ethical and legal compliance.

### 3. GitHub Codespaces (Recommended)

If you are using GitHub Codespaces, the `.devcontainer/devcontainer.json` file will automatically set up the environment for you. Just open the repository in Codespaces, and it will:

*   Install Python 3.11.
*   Install all dependencies from `requirements.txt`.
*   Install Playwright browsers.

### 4. Local Setup

If running locally:

1.  **Create a virtual environment and install dependencies:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

2.  **Install Playwright browsers:**

    ```bash
    playwright install
    ```

## Running the Bot

Use the provided `start.sh` script to run the bot. This script activates the virtual environment, installs dependencies (if not already installed), installs Playwright browsers, validates configuration, and starts the bot.

```bash
./scripts/start.sh
```

To run the bot in the background (e.g., using `nohup` or `screen`):

```bash
nohup ./scripts/start.sh > bot.log 2>&1 &
```

## Running Tests

Use the `run_tests.sh` script to execute tests. It supports various options:

```bash
./scripts/run_tests.sh             # Run all tests
./scripts/run_tests.sh unit        # Run only unit tests
./scripts/run_tests.sh integration # Run only integration tests
./scripts/run_tests.sh coverage    # Run tests and generate a coverage report
./scripts/run_tests.sh verbose     # Run all tests with verbose output
```

## Deployment Notes

*   **GitHub Codespaces:** The `devcontainer.json` is configured for a seamless development experience. For production, you might consider building a Docker image based on the provided `Dockerfile` (if uncommented and configured).
*   **Docker:** A `Dockerfile` (optional) is included for containerized deployment. Build and run the image, passing environment variables.
*   **VPS/Server:** For a Virtual Private Server, you can run the bot using `systemd` for process management to ensure it restarts automatically and runs reliably.

## Ethical Considerations

This bot is designed to interact with `ivasms.com` for OTP retrieval. **It is imperative that you have explicit, written permission from the website owner to access and scrape data from their platform.** The `OWNER_PERMISSION_ACKNOWLEDGED` and `PERMISSION_REFERENCE` environment variables are included to enforce this requirement. Failure to obtain proper authorization may lead to legal consequences and violation of terms of service.

## License

This project is licensed under the MIT License - see the LICENSE file for details. (Note: A `LICENSE` file is not included in this deliverable but should be added in a real project.)

