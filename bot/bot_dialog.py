from flask import request, jsonify
import requests

BACKEND_API = 'http://localhost:5000/api/opportunity'
REPORT_URL = 'http://localhost:5000/api/opportunities/report'

# This is a simplified handler for demo purposes

def handle_teams_message():
    data = request.json
    # Expecting a Teams message with opportunity details in text
    text = data.get('text', '')
    # Parse fields from text (very basic demo)
    # Example: "Project: Road Upgrade, Country: Kenya, Sector: roads, Deadline: 2024-07-01"
    fields = {}
    for part in text.split(','):
        if ':' in part:
            k, v = part.split(':', 1)
            fields[k.strip().lower()] = v.strip()
    opp_data = {
        'project_name': fields.get('project', ''),
        'client': fields.get('client', 'Teams User'),
        'country': fields.get('country', ''),
        'sector': fields.get('sector', ''),
        'summary': fields.get('summary', ''),
        'deadline': fields.get('deadline', ''),
        'program': '',
        'budget': '',
        'url': ''
    }
    try:
        resp = requests.post(BACKEND_API, json=opp_data)
        result = resp.json()
        reply = f"Score: {result['score']}%\nPartners: " + ", ".join([p['name'] for p in result['recommended_partners']])
        reply += f"\n[Download Report]({REPORT_URL})"
    except Exception as e:
        reply = f"Error processing opportunity: {e}"
    return jsonify({"type": "message", "text": reply}) 