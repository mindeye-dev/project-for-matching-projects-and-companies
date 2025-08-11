# Scheduled Scraping Setup

This directory contains the scheduled scraper that runs daily to collect opportunities from the World Bank.

## Files

- `scheduled_scraper.py` - Main scheduled scraper with APScheduler
- `run_scraper_now.py` - Script to run scraper immediately for testing
- `Dockerfile.scheduler` - Docker setup for the scheduled service
- `requirements.txt` - Python dependencies including APScheduler

## How It Works

The scheduled scraper uses **APScheduler** to run the World Bank scraper daily at **9:00 AM**. It includes:

- ✅ **Daily scheduling** at 9:00 AM
- ✅ **Comprehensive logging** to `scheduled_scraper.log`
- ✅ **Error notifications** via Slack webhook
- ✅ **Proxy support** for anti-bot measures
- ✅ **Headless mode** for server deployment
- ✅ **Automatic restart** on failure

## Usage Options

### Option 1: Docker (Recommended)

```bash
# Start all services including scheduled scraper
docker-compose up -d

# View scraper logs
docker-compose logs -f scraper-scheduler

# Run scraper immediately for testing
docker-compose exec scraper-scheduler python run_scraper_now.py
```

### Option 2: Local Development

```bash
cd scrapers

# Install dependencies
pip install -r requirements.txt

# Start scheduler (runs daily at 9:00 AM)
python scheduled_scraper.py

# Run scraper immediately for testing
python run_scraper_now.py
```

## Environment Variables

Set these in your `.env` file or environment:

```bash
# Backend API endpoint
BACKEND_API=http://localhost:5000/api/opportunity

# Proxy API for anti-bot measures (optional)
PROXY_API_KEY=your_proxy_api_key

# Slack webhook for notifications (optional)
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Run in headless mode (recommended for servers)
HEADLESS=1
```

## Monitoring

### View Logs

```bash
# Docker logs
docker-compose logs -f scraper-scheduler

# Local logs
tail -f scrapers/scheduled_scraper.log
```

### Manual Testing

```bash
# Test scraper immediately
python run_scraper_now.py

# Test with specific environment
BACKEND_API=http://localhost:5000/api/opportunity python run_scraper_now.py
``` 