# Microsoft Teams Bot Setup Guide

This guide will help you set up and deploy the Microsoft Teams bot integration for the Bank Fintech Chatbot.

## Prerequisites

- Azure account with active subscription
- Microsoft Teams account
- Publicly accessible HTTPS endpoint for the bot
- Python backend server running

## Step 1: Register Bot in Azure Portal

1. **Go to Azure Portal** (https://portal.azure.com)

2. **Create Azure Bot Resource:**
   - Click "Create a resource"
   - Search for "Azure Bot"
   - Click "Create"
   - Fill in the form:
     - **Bot handle**: Choose a unique name (e.g., `bank-fintech-chatbot`)
     - **Subscription**: Select your subscription
     - **Resource group**: Create new or use existing
     - **Pricing tier**: Free (F0) for testing, Standard (S1) for production
     - **Microsoft App ID**: Click "Create new" (we'll configure this next)
   - Click "Review + create" then "Create"

3. **Register Application in Azure AD:**
   - Go to Azure Active Directory → App registrations
   - Click "New registration"
   - **Name**: `Bank Fintech Chatbot Bot`
   - **Supported account types**: Accounts in any organizational directory and personal Microsoft accounts
   - **Redirect URI**: Leave blank for now
   - Click "Register"
   - **Copy the Application (client) ID** - this is your `TEAMS_APP_ID`
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Add description and expiration
   - **Copy the secret value immediately** - this is your `TEAMS_APP_PASSWORD` (you won't see it again!)

## Step 2: Configure Bot in Azure Portal

1. **Go back to your Azure Bot resource**

2. **Configure Bot Settings:**
   - **Messaging endpoint**: `https://your-domain.com/api/teams/messages`
     - Replace `your-domain.com` with your actual domain
     - Must be HTTPS
   - **Microsoft App ID**: Paste the Application ID from Step 1
   - **Microsoft App password**: Paste the client secret from Step 1
   - Click "Apply"

3. **Enable Microsoft Teams Channel:**
   - In your Azure Bot resource, go to "Channels"
   - Click "Microsoft Teams"
   - Click "Apply"
   - The bot is now configured for Teams!

## Step 3: Configure Environment Variables

Add the following to your `backend/.env` file:

```env
TEAMS_APP_ID=your-application-id-from-azure
TEAMS_APP_PASSWORD=your-client-secret-from-azure
```

## Step 4: Deploy Backend with HTTPS

The bot endpoint must be publicly accessible via HTTPS. Options:

### Option A: Deploy to Azure App Service
1. Create an App Service in Azure
2. Deploy your Flask app
3. Enable HTTPS (automatic with App Service)
4. Update messaging endpoint in Azure Bot

### Option B: Use ngrok for Development
1. Install ngrok: https://ngrok.com/
2. Start your Flask app locally
3. Run: `ngrok http 5000`
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
5. Update messaging endpoint: `https://abc123.ngrok.io/api/teams/messages`
6. **Note**: ngrok URLs change on restart, so update Azure Bot settings each time

### Option C: Deploy to Other Cloud Providers
- AWS (Elastic Beanstalk, EC2 with Load Balancer)
- Google Cloud Platform (App Engine, Cloud Run)
- Heroku
- DigitalOcean

## Step 5: Test the Bot

1. **Verify Health Endpoint:**
   ```bash
   curl https://your-domain.com/api/teams/health
   ```
   Should return: `{"status": "healthy", ...}`

2. **Add Bot to Teams:**
   - Open Microsoft Teams
   - Go to Apps (left sidebar)
   - Search for your bot name
   - Click "Add" or "Get"
   - Start a chat with the bot

3. **Test Commands:**
   - Send: "Hello"
   - Send: "Show me all projects in Egypt"
   - Send: "Generate a report"

## Step 6: Publish Bot (Optional)

To make your bot available to other Teams users:

1. **Create Bot Manifest:**
   - Go to Azure Bot → Channels → Microsoft Teams
   - Click "Edit" next to your bot
   - Fill in bot details (name, description, icons)
   - Download the manifest

2. **Submit for Review (if making public):**
   - Go to Teams App Studio or Developer Portal
   - Upload your manifest
   - Submit for Microsoft review

## Troubleshooting

### Bot Not Responding

1. **Check Health Endpoint:**
   ```bash
   curl https://your-domain.com/api/teams/health
   ```

2. **Check Backend Logs:**
   - Look for errors in Flask logs
   - Check for authentication errors

3. **Verify Endpoint URL:**
   - Must be HTTPS
   - Must be publicly accessible
   - Must match exactly in Azure Bot settings

4. **Check Environment Variables:**
   - Verify `TEAMS_APP_ID` and `TEAMS_APP_PASSWORD` are set
   - Restart backend after changing .env

### Authentication Errors

- Verify App ID and Password are correct
- Check that client secret hasn't expired
- Regenerate secret if needed

### Bot Not Appearing in Teams

- Wait a few minutes after adding channel
- Try searching for bot by App ID
- Check Azure Bot resource status

### Messages Not Being Received

- Verify messaging endpoint is correct
- Check that endpoint is accessible from internet
- Review backend logs for incoming requests
- Test with ngrok to verify local setup works

## Security Best Practices

1. **Never commit secrets to git**
   - Use `.env` file (already in .gitignore)
   - Use Azure Key Vault for production

2. **Use HTTPS only**
   - Teams requires HTTPS endpoints
   - Use valid SSL certificates

3. **Rotate secrets regularly**
   - Update client secrets periodically
   - Update environment variables when rotating

4. **Monitor bot activity**
   - Review logs regularly
   - Set up alerts for errors

## API Endpoints

### POST /api/teams/messages
- **Purpose**: Receive activities from Teams
- **Authentication**: Handled by Bot Framework
- **Content-Type**: application/json

### GET /api/teams/health
- **Purpose**: Health check for Azure Bot Service
- **Response**: JSON with status information

## Bot Capabilities

The bot supports:
- ✅ Text messages
- ✅ Conversation updates (when added to team)
- ✅ Member added notifications
- ✅ Typing indicators
- ✅ Session management
- ✅ Error handling

## Support

For issues:
1. Check backend logs
2. Review Azure Bot resource logs
3. Test health endpoint
4. Verify configuration

## Additional Resources

- [Microsoft Bot Framework Documentation](https://docs.microsoft.com/en-us/azure/bot-service/)
- [Teams Bot Development Guide](https://docs.microsoft.com/en-us/microsoftteams/platform/bots/how-to/rate-limit)
- [Bot Framework Python SDK](https://github.com/microsoft/botbuilder-python)
