from flask import Blueprint, request, jsonify, send_file, current_app
from app.models import Opportunity, Partner
from app.models import db
from app.scrapers_score_of_companies.company_scraper_scorer import (
    get_three_suitable_companies_data,
)
import os

import pandas as pd
import io
from flask_jwt_extended import jwt_required
from app.chatbot import get_AI_message

api_bp = Blueprint("api", __name__)


@api_bp.route("/opportunity", methods=["POST"])
@jwt_required()
def submit_opportunity():
    """
    Receive, score, save, and return a new opportunity.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    try:
        opp = Opportunity(
            project_name=data.get("project_name"),
            client=data.get("client"),
            country=data.get("country"),
            sector=data.get("sector"),
            summary=data.get("summary"),
            deadline=data.get("deadline"),
            program=data.get("program"),
            budget=data.get("budget"),
            url=data.get("url"),
            found=data.get("found"),
            recommended_partners=[],
        )
        db.session.add(opp)
        db.session.commit()

        return jsonify({"id": opp.id})
    except Exception as e:
        current_app.logger.error(f"Error submitting opportunity: {e}")
        return jsonify({"error": "Failed to submit opportunity"}), 500


@api_bp.route("/opportunities", methods=["GET"])
@jwt_required()
def list_opportunities():
    """
    List all opportunities, optionally filtered by country/sector.
    """
    country = request.args.get("country")
    sector = request.args.get("sector")
    query = Opportunity.query
    if country:
        query = query.filter(Opportunity.country.ilike(f"%{country}%"))
    if sector:
        query = query.filter(Opportunity.sector.ilike(f"%{sector}%"))
    results = query.order_by(Opportunity.id.desc()).all()
    out = []
    for o in results:
        out.append(
            {
                "id": o.id,
                "project_name": o.project_name,
                "client": o.client,
                "country": o.country,
                "sector": o.sector,
                "summary": o.summary,
                "deadline": o.deadline,
                "program": o.program,
                "budget": o.budget,
                "url": o.url,
                "found": o.found,
                "recommended_partners": o.recommended_partners,
            }
        )
    return jsonify(out)


@api_bp.route("/opportunities/report", methods=["GET"])
@jwt_required()
def download_report():
    """
    Generate and return an Excel report of all opportunities.
    """
    try:
        results = Opportunity.query.order_by(Opportunity.id.desc()).all()
        rows = []
        for o in results:
            rows.append(
                {
                    "Project Name": o.project_name,
                    "Client": o.client,
                    "Country": o.country,
                    "Sector": o.sector,
                    "Summary": o.summary,
                    "Submission Deadline": o.deadline,
                    "Program": o.program,
                    "Budget": o.budget,
                    "URL": o.url,
                    "Found": o.found,
                    "Recommended Partners": o.recommended_partners,
                }
            )
        df = pd.DataFrame(rows)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Opportunities")
        output.seek(0)
        return send_file(
            output, download_name="opportunities_report.xlsx", as_attachment=True
        )
    except Exception as e:
        current_app.logger.error(f"Error generating report: {e}")
        return jsonify({"error": "Failed to generate report"}), 500


@api_bp.route("/get-partners", methods=["POST"])
@jwt_required()
def find_partners_for_opportunity():
    """
    Given opportunity details, find suitable partners.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    try:
        three_suitable_matched_score_and_companies_data = get_three_suitable_matched_scores_and_companies_data(data)

        if three_suitable_matched_score_and_companies_data.__len__() == 0:
            return jsonify({"message": "No suitable partners found"})
        # Query opportunity, update opportunity table
        opportunity = Opportunity.query.get(data.id)
        if not opportunity:
            return False  # or handle error
        opportunity.found = True
        
        three_matched_scores_and_recommended_partners_ids = [
            {
                "matched_score": item["matched_score"],
                "company_id": item["company_data"]["id"]  # or item["company_data"].id if object
            }
            for item in three_suitable_matched_score_and_companies_data
        ]
        
        opportunity.three_matched_scores_and_recommended_partners_ids=three_matched_scores_and_recommended_partners_ids
        db.session.commit()

        return jsonify(three_suitable_matched_score_and_companies_data)
    except Exception as e:
        current_app.logger.error(f"Error finding partners: {e}")
        return jsonify({"error": "Failed to find partners"}), 500


# user want to fine new opportunities. In this case, scraping is executed and if there is one oppotunity adn click star to thisgithub.o
@api_bp.route("/scrape_latest_opportunities", methods=["GET"])
@jwt_required()
def find_new_opportunities():
    """
    Placeholder for finding new opportunities from external sources.
    """
    
    # scrape to find latest opportunities

    # This is a placeholder. In a real implementation, you would integrate
    # with external APIs or web scraping logic to find new opportunities.
    return jsonify({"message": "Functionality not yet implemented."}), 501


# user want to get message from AI chatbot
@api_bp.route("/message_from_chatbot", methods=["POST"])
@jwt_required()
def message_from_chatbot():
    """
    Placeholder for AI chatbot interaction.
    """
    data = request.json
    if not data or not data.get("message"):
        return jsonify({"error": "Missing message in JSON body"}), 400
    user_message = data["message"]
    # This is a placeholder. In a real implementation, you would integrate
    # with an AI service to get a response.

    bot_response = get_AI_message(user_message)
    return jsonify({"response": bot_response})
