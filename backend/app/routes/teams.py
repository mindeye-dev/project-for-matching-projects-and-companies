from flask import Blueprint, request, current_app, jsonify
from app.teams_bot import TeamsBot
import logging

logger = logging.getLogger(__name__)

teams_bp = Blueprint('teams', __name__)

# Store bot instance to avoid recreating it for each request
_bot_instance = None

def get_bot_instance():
    """Get or create Teams bot instance"""
    global _bot_instance
    if _bot_instance is None:
        app_id = current_app.config.get('TEAMS_APP_ID')
        app_password = current_app.config.get('TEAMS_APP_PASSWORD')
        
        if not app_id or not app_password:
            raise ValueError('Teams bot credentials not configured')
        
        _bot_instance = TeamsBot(app_id, app_password)
    
    return _bot_instance

@teams_bp.route('/messages', methods=['POST'])
def messages():
    """
    Handle incoming messages from Teams
    Note: The route is '/messages' because the blueprint is registered with '/api/teams' prefix,
    so the full path will be '/api/teams/messages'
    
    This endpoint receives activities from Microsoft Teams via Azure Bot Service.
    """
    try:
        # Get Teams bot instance
        bot = get_bot_instance()
        
        # Process the incoming activity
        response = bot.process_activity(request)
        return response
    except ValueError as e:
        logger.error(f"Teams bot configuration error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Error processing Teams message: {e}", exc_info=True)
        return jsonify({'error': 'Failed to process message'}), 500

@teams_bp.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint for Teams bot
    Used by Azure Bot Service to verify the bot is running
    """
    try:
        # Check if credentials are configured
        app_id = current_app.config.get('TEAMS_APP_ID')
        app_password = current_app.config.get('TEAMS_APP_PASSWORD')
        
        if not app_id or not app_password:
            return jsonify({
                'status': 'unhealthy',
                'message': 'Teams bot credentials not configured'
            }), 503
        
        return jsonify({
            'status': 'healthy',
            'service': 'teams-bot',
            'endpoint': '/api/teams/messages'
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503