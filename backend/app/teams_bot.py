from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext, ActivityHandler
from botbuilder.schema import Activity, ActivityTypes, ChannelAccount
from flask import Response, Request, current_app
import asyncio
import logging
from app.chatbot import process_message, create_user_session, chat_with_AI, get_user_sessions_dict
from app.models import User, db
import hashlib

logger = logging.getLogger(__name__)

class TeamsBot:
    def __init__(self, app_id: str, app_password: str):
        """
        Initialize the Teams bot with Azure AD app credentials
        """
        settings = BotFrameworkAdapterSettings(app_id, app_password)
        self.adapter = BotFrameworkAdapter(settings)
        
        # Error handler
        async def on_error(context: TurnContext, error: Exception):
            logger.error(f"Teams bot error: {error}", exc_info=True)
            try:
                await context.send_activity("I encountered an error processing your request. Please try again.")
            except Exception as e:
                logger.error(f"Error sending error message: {e}")
            
        self.adapter.on_turn_error = on_error

    def _get_or_create_teams_user(self, teams_user_id: str, teams_user_name: str = None) -> User:
        """
        Get or create a user account for a Teams user.
        Teams users are identified by their Teams user ID.
        """
        # Create a deterministic email from Teams user ID
        email = f"teams_{hashlib.md5(teams_user_id.encode()).hexdigest()}@teams.local"
        
        user = User.query.filter_by(email=email).first()
        if not user:
            # Create new user for Teams
            user = User(
                email=email,
                password="",  # Teams users don't use password
                role="user"
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created new Teams user: {email}")
        
        return user

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Handle incoming message activities from Teams
        """
        try:
            # Get the message text
            text = turn_context.activity.text.strip() if turn_context.activity.text else ""
            
            if not text:
                await turn_context.send_activity("Please send me a message. I can help you find projects, companies, and generate reports.")
                return
            
            # Get Teams user information
            teams_user_id = turn_context.activity.from_property.id if turn_context.activity.from_property else None
            teams_user_name = turn_context.activity.from_property.name if turn_context.activity.from_property else "Teams User"
            
            # Show typing indicator
            await self._send_typing_activity(turn_context)
            
            # Get or create user account
            with current_app.app_context():
                user = self._get_or_create_teams_user(teams_user_id or "unknown", teams_user_name)
                
                # Get or create session for this user
                sessions = get_user_sessions_dict(user.id)
                session_id = sessions[0]["id"] if sessions else None
                
                if not session_id:
                    # Create new session
                    session = create_user_session(user.id)
                    session_id = session["id"]
                
                # Process the message using existing chatbot logic with session
                response = await self._process_message_with_session(user.id, text, session_id)
            
            # Send response back to Teams
            await turn_context.send_activity(response)
            
        except Exception as e:
            logger.error(f"Error in on_message_activity: {e}", exc_info=True)
            await turn_context.send_activity("I encountered an error processing your message. Please try again.")

    async def _process_message_with_session(self, user_id: int, message: str, session_id: int) -> str:
        """
        Process message with user session context
        """
        try:
            loop = asyncio.get_event_loop()
            # Use chat_with_AI which handles session management
            result = await loop.run_in_executor(
                None, 
                lambda: chat_with_AI(user_id, message, session_id)
            )
            return result if result else "Sorry, I couldn't process your request. Please try again."
        except Exception as e:
            logger.error(f"Error processing message with session: {e}")
            return "An error occurred while processing your message. Please try again."

    async def _send_typing_activity(self, turn_context: TurnContext):
        """
        Send typing indicator to show bot is processing
        """
        try:
            typing_activity = Activity(type=ActivityTypes.typing)
            await turn_context.send_activity(typing_activity)
        except Exception as e:
            logger.warning(f"Could not send typing indicator: {e}")

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        """
        Handle when members are added to the conversation
        """
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_message = (
                    "Hello! I'm your Bank Fintech Chatbot. I can help you:\n"
                    "- Find and search for bank projects\n"
                    "- Match projects with suitable companies\n"
                    "- Generate Excel reports\n"
                    "- Answer questions about opportunities\n\n"
                    "Just ask me anything, for example:\n"
                    "- 'Show me all projects in Egypt'\n"
                    "- 'Find suitable companies for project X'\n"
                    "- 'Generate a report of all opportunities'"
                )
                await turn_context.send_activity(welcome_message)

    async def on_conversation_update_activity(self, turn_context: TurnContext):
        """
        Handle conversation update activities (like when bot is added to a team)
        """
        if turn_context.activity.members_added:
            await self.on_members_added_activity(
                turn_context.activity.members_added,
                turn_context
            )
            
    def process_activity(self, request: Request) -> Response:
        """
        Process incoming activity from Teams (synchronous wrapper for async adapter)
        """
        try:
            content_type = request.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                logger.warning(f"Invalid content type: {content_type}")
                return Response(status=415)

            body = request.json
            if not body:
                logger.warning("Empty request body")
                return Response(status=400)

            activity = Activity().deserialize(body)
            auth_header = request.headers.get("Authorization", "")

            # Create a response object that will be populated by the adapter
            response = Response(status=201)
            
            async def aux_func(turn_context):
                # Handle different activity types
                if turn_context.activity.type == ActivityTypes.message:
                    await self.on_message_activity(turn_context)
                elif turn_context.activity.type == ActivityTypes.conversation_update:
                    await self.on_conversation_update_activity(turn_context)
                elif turn_context.activity.type == ActivityTypes.members_added:
                    await self.on_members_added_activity(
                        turn_context.activity.members_added,
                        turn_context
                    )
                else:
                    logger.info(f"Unhandled activity type: {turn_context.activity.type}")
            
            # Run the async adapter in a new event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Process the activity
            loop.run_until_complete(
                self.adapter.process_activity(activity, auth_header, aux_func)
            )
            
            return response
        except Exception as e:
            logger.error(f"Error in process_activity: {e}", exc_info=True)
            return Response(status=500, response=f"Internal server error: {str(e)}")