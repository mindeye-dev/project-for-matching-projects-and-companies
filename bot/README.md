# Microsoft Teams Bot

Conversational bot for submitting opportunities, querying scores, and downloading reports directly from Teams.

## Features
- Accept opportunity descriptions via chat/adaptive cards
- Relay to backend for scoring and partner lookup
- Return scores, partners, and report links

## Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Integration
- Register bot with Microsoft Teams
- Configure backend endpoint and authentication 