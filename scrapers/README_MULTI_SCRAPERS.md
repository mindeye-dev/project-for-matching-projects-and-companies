# Multi-Bank Scraping System

This directory contains scrapers for multiple development banks and a scheduled system to run them daily.

## Available Scrapers

### 1. World Bank (`wb_selenium_production.py`)
- **URL**: https://projects.worldbank.org/en/projects-operations/procurement
- **Schedule**: Daily at 9:00 AM
- **Features**: Detail page scraping, comprehensive logging, error notifications

### 2. African Development Bank (`afdb_scraper.py`)
- **URL**: https://www.afdb.org/en/projects-and-operations/procurement
- **Schedule**: Daily at 10:00 AM
- **Features**: Basic scraping with error handling

### 3. Asian Development Bank (`adb_scraper.py`)
- **URL**: https://www.adb.org/projects/procurement
- **Schedule**: Daily at 11:00 AM
- **Features**: Basic scraping with error handling

### 4. Inter-American Development Bank (`idb_scraper.py`)
- **URL**: https://www.iadb.org/en/projects/procurement
- **Schedule**: Daily at 12:00 PM
- **Features**: Basic scraping with error handling

## Scheduled Scraper (`scheduled_scraper.py`)

The main scheduler that runs all scrapers at different times to avoid conflicts:

- **9:00 AM**: World Bank
- **10:00 AM**: African Development Bank
- **11:00 AM**: Asian Development Bank
- **12:00 PM**: Inter-American Development Bank

## Usage

### Docker (Recommended)
```bash
# Start all services including scheduled scraper
docker-compose up -d

# View scraper logs
docker-compose logs -f scraper-scheduler

# Run specific scraper immediately for testing
docker-compose exec scraper-scheduler python afdb_scraper.py
```

### Local Development
```bash
cd scrapers

# Install dependencies
pip install -r requirements.txt

# Start scheduler (runs all scrapers daily)
python scheduled_scraper.py

# Run individual scrapers for testing
python afdb_scraper.py
python adb_scraper.py
python idb_scraper.py
```

## Environment Variables

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

# Individual scraper logs
tail -f scrapers/scheduled_scraper.log
tail -f scrapers/afdb_scraper.log
tail -f scrapers/adb_scraper.log
tail -f scrapers/idb_scraper.log
```

### Manual Testing
```bash
# Test individual scrapers
python afdb_scraper.py
python adb_scraper.py
python idb_scraper.py
``` 