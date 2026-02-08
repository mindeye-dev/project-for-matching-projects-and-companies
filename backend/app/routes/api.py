from flask import Blueprint, request, jsonify, send_file, current_app
from app.models import Opportunity, Partner, Session
from app.models import db
from app.scrapers_score_of_companies.company_scraper_scorer import (
    get_three_suitable_matched_scores_and_companies_data,
)

from app.scrapers_of_projects.scheduled_scraper import run_scraping

import os

import pandas as pd
import io
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.chatbot import create_user_session, delete_user_session, chat_with_AI, get_session_messages_dict, get_user_sessions_dict

api_bp = Blueprint("api", __name__)


@api_bp.route("/fetchopportunities", methods=["GET"])
@jwt_required()
def list_opportunities():
    """
    List all opportunities, optionally filtered by country/sector.
    """
    country = request.args.get("country")
    sector = request.args.get("sector")
    print("starting to send opportunities")
    print("country is ", country)
    print("sector is ", sector)
    query = Opportunity.query
    print("query is ", query)
    if country:
        query = query.filter(Opportunity.country.ilike(f"%{country}%"))
    if sector:
        query = query.filter(Opportunity.sector.ilike(f"%{sector}%"))
    print("filtered query is ", query)
    results = query.order_by(Opportunity.id.desc()).all()
    # print("results are ", results)
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
    Expects JSON with opportunity_id or full opportunity data.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    try:
        # If opportunity_id is provided, fetch the opportunity from database
        if "opportunity_id" in data:
            opportunity = Opportunity.query.get(data["opportunity_id"])
            if not opportunity:
                return jsonify({"error": "Opportunity not found"}), 404
            project_data = {
                "id": opportunity.id,
                "project_name": opportunity.project_name,
                "client": opportunity.client,
                "country": opportunity.country,
                "sector": opportunity.sector,
                "summary": opportunity.summary,
                "deadline": opportunity.deadline,
                "program": opportunity.program,
                "budget": opportunity.budget,
                "url": opportunity.url,
            }
        else:
            # Use provided data, but ensure it has an id if it's an existing opportunity
            project_data = data
            if "id" not in project_data and "url" in project_data:
                # Try to find existing opportunity by URL
                existing = Opportunity.query.filter_by(url=project_data["url"]).first()
                if existing:
                    project_data["id"] = existing.id
        
        three_suitable_matched_score_and_companies_data = (
            get_three_suitable_matched_scores_and_companies_data(project_data)
        )

        return jsonify(three_suitable_matched_score_and_companies_data)
    except Exception as e:
        current_app.logger.error(f"Error finding partners: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to find partners: {str(e)}"}), 500
 

# user want to fine new opportunities. In this case, scraping is executed and if there is one oppotunity adn click star to thisgithub.o
@api_bp.route("/scrape_latest_opportunities", methods=["GET"])
@jwt_required()
def find_new_opportunities():
    """
    Placeholder for finding new opportunities from external sources.
    """

    # scrape to find latest opportunities
    run_scraping()

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
    user_id = get_jwt_identity()
    data = request.json
    if not data or not data.get("message"):
        return jsonify({"error": "Missing message in JSON body"}), 400
    user_message = data["message"]
    session_id = data.get("session_id")
    # This is a placeholder. In a real implementation, you would integrate
    # with an AI service to get a response.

    bot_response = chat_with_AI(user_id, user_message, session_id)
    return jsonify({"response": bot_response})


@api_bp.route("/create_session", methods=["POST"])
@jwt_required()
def create_session():
    print("-----------------------------")
    user_id = get_jwt_identity()
    print(user_id)
    session = create_user_session(user_id)
    return jsonify(session)


# -------------------------------
# Delete a session
# -------------------------------
@api_bp.route("/delete_session/<int:session_id>", methods=["DELETE"])
@jwt_required()
def delete_session(session_id):
    print("deleting session ", session_id)
    user_id = get_jwt_identity()
    result = delete_user_session(user_id, session_id)
    print(result)
    return jsonify(result)


# -------------------------------
# Get all messages from a session
# -------------------------------
@api_bp.route("/session/<int:session_id>/messages", methods=["GET"])
@jwt_required()
def get_session_messages(session_id):
    user_id = get_jwt_identity()
    # Verify session belongs to user
    session_obj = Session.query.filter_by(id=session_id, user_id=user_id).first()
    if not session_obj:
        return jsonify({"error": "Session not found"}), 404

    messages = get_session_messages_dict(session_id)
    return jsonify({"messages": messages})


# -------------------------------
# Get all sessions of the user
# -------------------------------
@api_bp.route("/sessions", methods=["GET"])
@jwt_required()
def get_user_sessions():
    user_id = get_jwt_identity()
    sessions = get_user_sessions_dict(user_id)
    return jsonify({"sessions": sessions})



