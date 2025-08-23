# Scrapers

Modular Python scrapers for extracting opportunities from development bank and donor websites.

## Features
- Daily scheduled scraping
- CAPTCHA bypass hooks
- Modular per-bank scrapers

## Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py  # or python sample_scraper.py
```

## Adding a New Scraper
- Add a new Python module in this directory
- Register it in the scheduler 