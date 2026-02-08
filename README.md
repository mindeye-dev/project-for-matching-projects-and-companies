# Bank Fintech Chatbot Project

A comprehensive AI-powered platform for scraping bank projects, matching them with suitable companies from LinkedIn, and providing an intelligent chatbot interface for project discovery and management.

## 🧩 About

This project provides an intelligent system for:
- **Scraping consultancy opportunities** from major development banks (World Bank, African Development Bank, etc.)
- **Matching projects with suitable companies** using AI-powered scoring based on industry, location, and project requirements
- **Intelligent chatbot interface** that helps users discover projects, find suitable partners, and generate reports
- **Microsoft Teams integration** for seamless collaboration

The system uses LangChain and OpenAI for natural language processing, automated web scraping for project discovery, and LinkedIn API integration for company matching.

## ✨ Features

- **Automated Project Scraping**: Scheduled scraping of projects from major development banks
- **AI-Powered Company Matching**: Intelligent matching of projects with suitable companies using OpenAI
- **LinkedIn Integration**: Company profile scraping and matching based on industry and location codes
- **Intelligent Chatbot**: SQL-powered chatbot that can answer questions about projects, companies, and generate reports
- **Microsoft Teams Integration**: Bot integration for Teams collaboration
- **User Authentication**: JWT-based authentication with user and admin roles
- **Excel Report Generation**: Export opportunities and matched companies to Excel
- **Session Management**: Multi-session chat support with message history

## 🖼️ ScreenShoot

### Application Screenshots

![Screen 1](ScreenShoot/screen%201.png)

*Application interface showing the main dashboard and project management features*

## 🧠 Tech Stack

### Backend
- **Python 3.x**
- **Flask**: Web framework
- **SQLAlchemy**: Database ORM
- **LangChain**: AI/LLM framework
- **OpenAI API**: GPT-4 for matching and chatbot
- **Perplexity API**: Industry/location code matching
- **Unipile API**: LinkedIn data scraping
- **Flask-JWT-Extended**: Authentication
- **APScheduler**: Task scheduling

### Frontend
- **React 18**
- **TypeScript**
- **Vite**: Build tool
- **Tailwind CSS**: Styling
- **shadcn/ui**: UI components
- **React Router**: Routing
- **TanStack Query**: Data fetching

### Database
- **SQLite** (development)
- **PostgreSQL** (production, via Docker)

## ⚙️ Installation

### Prerequisites
- Python 3.8+
- Node.js 18+
- Docker and Docker Compose (optional, for containerized deployment)

### Backend Setup

1. **Navigate to backend directory:**
```bash
cd backend
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
Create a `.env` file in the `backend` directory (see `.env.example` for required variables):
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. **Initialize database:**
```bash
python run.py
# The database will be created automatically on first run
```

### Frontend Setup

1. **Navigate to frontend directory:**
```bash
cd frontend/global-roads-scout
```

2. **Install dependencies:**
```bash
npm install
```

3. **Start development server:**
```bash
npm run dev
```

### Docker Setup (Optional)

1. **Build and start all services:**
```bash
docker-compose up --build
```

This will start:
- Backend API on port 5000
- Frontend on port 3000
- PostgreSQL database on port 5432
- Scheduled scraper service

## 🚀 Usage

### Starting the Application

1. **Start Backend:**
```bash
cd backend
python run.py
```
Backend will run on `http://127.0.0.1:5000`

2. **Start Frontend:**
```bash
cd frontend/global-roads-scout
npm run dev
```
Frontend will run on `http://localhost:5173` (Vite default)

3. **Access the application:**
Open your browser and navigate to `http://localhost:5173`

### Key Workflows

#### 1. User Registration and Login
- Sign up with email and password
- Login to get JWT token
- Access protected endpoints

#### 2. Scraping Projects
- Projects are automatically scraped on a schedule
- Manual scraping: Use the `/api/scrape_latest_opportunities` endpoint
- Projects are stored in the database with details (name, client, country, sector, summary, deadline, budget, URL)

#### 3. Finding Suitable Companies
- Select a project from the opportunities list
- Click "Find Suitable Companies"
- System will:
  - Match industry and location codes using LinkedIn codes
  - Search LinkedIn for companies matching criteria
  - Score each company against the project using AI
  - Return top 3 matches with scores

#### 4. Chatbot Interaction
- Create a new chat session
- Ask questions about projects, companies, or request reports
- Examples:
  - "Show me all projects in Egypt"
  - "Find suitable companies for project X"
  - "Generate an Excel report of all opportunities"

#### 5. Microsoft Teams Integration
- Configure Teams bot credentials in `.env`
- Deploy backend with Teams endpoint: `/api/teams/messages`
- Users can interact with the bot directly in Teams
- **Features:**
  - Automatic user session management for Teams users
  - Typing indicators for better UX
  - Welcome messages when bot is added to team
  - Full chatbot functionality in Teams
- **Setup:** See `backend/TEAMS_SETUP.md` for detailed setup instructions

## 🧾 Configuration

### Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

```env
# Database
SQLALCHEMY_DATABASE_URI=sqlite:///app.db

# JWT
JWT_SECRET_KEY=your-secret-key-here

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Perplexity (for industry/location code matching)
PERPLEXITY_API_KEY=your-perplexity-api-key

# LinkedIn/Unipile
LINKEDIN_ACCOUNT_ID=your-linkedin-account-id
UNIPILE_API_KEY=your-unipile-api-key
UNIPILE_DNS=api.unipile.com

# Microsoft Teams
TEAMS_APP_ID=your-teams-app-id
TEAMS_APP_PASSWORD=your-teams-app-password

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:5173
```

See `.env.example` for a complete template.

## 📜 API Documentation

### Authentication Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token

### Opportunity Endpoints

- `GET /api/fetchopportunities` - List all opportunities (with optional country/sector filters)
- `GET /api/opportunities/report` - Download Excel report of all opportunities
- `POST /api/get-partners` - Find suitable partners for an opportunity
- `GET /api/scrape_latest_opportunities` - Manually trigger project scraping

### Chatbot Endpoints

- `POST /api/create_session` - Create a new chat session
- `GET /api/sessions` - Get all user sessions
- `DELETE /api/delete_session/<session_id>` - Delete a session
- `GET /api/session/<session_id>/messages` - Get messages for a session
- `POST /api/message_from_chatbot` - Send a message to the chatbot

### Teams Endpoints

- `POST /api/teams/messages` - Handle incoming Teams messages (main webhook endpoint)
- `GET /api/teams/health` - Health check endpoint for Azure Bot Service

## 🗄️ Database Schema

### Tables

- **user**: User accounts (email, password, role)
- **opportunity**: Scraped projects from banks
- **partner**: Companies matched with projects
- **match**: Relationship between opportunities and partners with scores
- **session**: Chat sessions for users
- **message**: Messages in chat sessions

## 🔧 Troubleshooting

### Common Issues

1. **LinkedIn API Rate Limits**
   - The system limits to 100 profiles per day
   - Check `max_daily_profiles` in `company_scraper_scorer.py`

2. **Industry/Location Code Matching Fails**
   - System uses local matching first, then falls back to Perplexity API
   - Check `industry_code.json` for available industry codes
   - Ensure `PERPLEXITY_API_KEY` is set

3. **Teams Bot Not Responding**
   - Verify `TEAMS_APP_ID` and `TEAMS_APP_PASSWORD` are correct
   - Check that the endpoint `/api/teams/messages` is accessible via HTTPS
   - Test health endpoint: `GET /api/teams/health`
   - Review backend logs for errors
   - Ensure messaging endpoint in Azure Bot matches your deployment URL
   - See `backend/TEAMS_SETUP.md` for detailed troubleshooting guide

4. **Database Connection Issues**
   - For SQLite: Ensure write permissions in the backend directory
   - For PostgreSQL: Verify connection string and credentials

## 📝 Project Structure

```
Project/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app initialization
│   │   ├── config.py             # Configuration
│   │   ├── models.py             # Database models
│   │   ├── chatbot.py            # LangChain chatbot logic
│   │   ├── teams_bot.py          # Teams bot handler
│   │   ├── routes/
│   │   │   ├── api.py            # Main API routes
│   │   │   ├── auth.py           # Authentication routes
│   │   │   └── teams.py          # Teams routes
│   │   ├── scrapers_of_projects/ # Project scrapers
│   │   └── scrapers_score_of_companies/ # Company matching
│   ├── run.py                    # Application entry point
│   └── requirements.txt          # Python dependencies
├── frontend/
│   └── global-roads-scout/       # React frontend
├── bot/                          # Standalone bot (if needed)
├── docker-compose.yml            # Docker configuration
└── README.md                     # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📬 Contact

For questions or support, please open an issue in the repository.

**Email:** generativebrain055@gmail.com  
**GitHub:** [@mindeye-dev](https://github.com/mindeye-dev)

## 🌟 Acknowledgements

- LangChain for AI/LLM framework
- OpenAI for GPT models
- Microsoft Bot Framework for Teams integration
- Unipile for LinkedIn data access
