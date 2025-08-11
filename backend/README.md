# Backend (Flask API)

This backend provides RESTful APIs for opportunity management, scoring, partner lookup, and Excel reporting.

## Features
- Receive and parse consultancy opportunities
- Automated scoring against consultancy profiles
- Partner lookup by country/sector
- Excel report generation
- Daily scraping scheduler

## Setup
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python run.py
```

## API Endpoints
- `POST /api/opportunity` — Submit and score an opportunity
- `GET /api/opportunities` — List/query opportunities
- `GET /api/opportunities/report` — Download Excel report
- `GET /api/partners?criteria=...` — Partner lookup 