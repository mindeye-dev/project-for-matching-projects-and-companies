# Consultancy Automation System

This monorepo contains all components for a consultancy automation platform that tracks, scores, and reports on development bank opportunities, with chat and web interfaces.

## Structure

- `backend/` — Flask REST API, scraping, scoring, partner lookup, Excel reporting
- `frontend/` — React SPA for opportunity management, scoring, and reporting
- `bot/` — Microsoft Teams chatbot (Python, Bot Framework)
- `scrapers/` — Modular web scrapers for bank/donor sites (with CAPTCHA bypass hooks)
- `shared/` — Shared models/utilities (optional, for future use)

## Quick Start

### Backend (Flask)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python run.py
```

### Frontend (React)
```bash
cd frontend
npm install
npm start
```

### Bot (Teams)
```bash
cd bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

### Scrapers
```bash
cd scrapers
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py  # or python sample_scraper.py
```

## Features
- Daily scraping of development bank opportunities
- Automated scoring against consultancy profiles
- Partner lookup by country/sector
- Excel report generation
- Web and Teams chat interfaces
- Modular, extensible, and ready for enterprise integration

## Bank Scraper Coverage

This system includes robust, modular scrapers for the following banks and databases:

| Bank/Database                                      | Script Name                | Status      |
|----------------------------------------------------|----------------------------|-------------|
| World Bank (WB)                                    | wb_scraper.py              | Implemented |
| African Development Bank (AfDB)                    | afdb_scraper.py            | Implemented |
| Asian Development Bank (ADB)                       | adb_scraper.py             | Implemented |
| Inter-American Development Bank (IDB)              | idb_scraper.py             | Implemented |
| European Investment Bank (EIB)                     | eib_scraper.py             | Scaffolded  |
| Agence Française de Développement (AFD)            | afd_scraper.py             | Scaffolded  |
| Islamic Development Bank (IsDB)                    | isdb_scraper.py            | Scaffolded  |
| Proparco                                           | proparco_scraper.py        | Scaffolded  |
| KfW Development Bank (Germany)                     | kfw_scraper.py             | Scaffolded  |
| United Nations Development Programme (UNDP)        | undp_scraper.py            | Implemented |
| European Bank for Reconstruction & Development (EBRD)| ebrd_scraper.py          | Implemented |
| International Finance Corporation (IFC)            | ifc_scraper.py             | Scaffolded  |
| FMO (Netherlands)                                  | fmo_scraper.py             | Scaffolded  |
| Multilateral Investment Guarantee Agency (MIGA)     | miga_scraper.py            | Scaffolded  |
| DeBIT Database (UChicago)                          | debit_scraper.py           | Scaffolded  |

- **Implemented**: Script exists and follows robust anti-bot/captcha/POSTing patterns.
- **Scaffolded**: Script template created; needs site-specific selector and logic updates.

All major development banks are now scaffolded or implemented. See PROJECT_GUIDANCE.md for a full status table and next steps.

## See each component's README for more details. 