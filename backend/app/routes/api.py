from flask import Blueprint, request, jsonify, send_file, current_app
from app.models import Opportunity
from app import db
from app.utils import score_opportunity, find_partners
import pandas as pd
import io
from flask_jwt_extended import jwt_required

api_bp = Blueprint('api', __name__)

@api_bp.route('/opportunity', methods=['POST'])
@jwt_required()
def submit_opportunity():
    """
    Receive, score, save, and return a new opportunity.
    """
    data = request.json
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400
    try:
        score = score_opportunity(data)
        opp = Opportunity(
            project_name=data.get('project_name'),
            client=data.get('client'),
            country=data.get('country'),
            sector=data.get('sector'),
            summary=data.get('summary'),
            deadline=data.get('deadline'),
            program=data.get('program'),
            budget=data.get('budget'),
            url=data.get('url'),
            score=score
        )
        db.session.add(opp)
        db.session.commit()
        partners = find_partners(data.get('country', ''), data.get('sector', ''))
        return jsonify({
            'id': opp.id,
            'score': score,
            'recommended_partners': partners
        })
    except Exception as e:
        current_app.logger.error(f"Error submitting opportunity: {e}")
        return jsonify({'error': 'Failed to submit opportunity'}), 500

@api_bp.route('/opportunities', methods=['GET'])
@jwt_required()
def list_opportunities():
    """
    List all opportunities, optionally filtered by country/sector.
    """
    country = request.args.get('country')
    sector = request.args.get('sector')
    query = Opportunity.query
    if country:
        query = query.filter(Opportunity.country.ilike(f"%{country}%"))
    if sector:
        query = query.filter(Opportunity.sector.ilike(f"%{sector}%"))
    results = query.order_by(Opportunity.id.desc()).all()
    out = []
    for o in results:
        out.append({
            'id': o.id,
            'project_name': o.project_name,
            'client': o.client,
            'country': o.country,
            'sector': o.sector,
            'summary': o.summary,
            'deadline': o.deadline,
            'program': o.program,
            'budget': o.budget,
            'url': o.url,
            'score': o.score
        })
    return jsonify(out)

@api_bp.route('/opportunities/report', methods=['GET'])
@jwt_required()
def download_report():
    """
    Generate and return an Excel report of all opportunities.
    """
    try:
        results = Opportunity.query.order_by(Opportunity.id.desc()).all()
        rows = []
        for o in results:
            rows.append({
                'Project Name': o.project_name,
                'Client': o.client,
                'Country': o.country,
                'Sector': o.sector,
                'Summary': o.summary,
                'Submission Deadline': o.deadline,
                'Program': o.program,
                'Budget': o.budget,
                'URL': o.url,
                'Score': o.score
            })
        df = pd.DataFrame(rows)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Opportunities')
        output.seek(0)
        return send_file(output, download_name='opportunities_report.xlsx', as_attachment=True)
    except Exception as e:
        current_app.logger.error(f"Error generating report: {e}")
        return jsonify({'error': 'Failed to generate report'}), 500

@api_bp.route('/partners', methods=['GET'])
@jwt_required()
def partner_lookup():
    """
    Lookup partners by country and sector.
    """
    country = request.args.get('country', '')
    sector = request.args.get('sector', '')
    try:
        partners = find_partners(country, sector)
        return jsonify(partners)
    except Exception as e:
        current_app.logger.error(f"Error in partner lookup: {e}")
        return jsonify({'error': 'Failed to lookup partners'}), 500 