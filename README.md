# CodeSentry — AI Automated Code Review System

CodeSentry is a full-stack AI-powered security code review platform that analyzes GitHub Pull Requests and automatically detects potential security vulnerabilities using a combination of deterministic security rules and AI-based analysis.

## Overview

CodeSentry allows developers to submit a public GitHub Pull Request URL and receive an automated review of the code changes. Findings are aggregated from multiple review agents, deduplicated, and presented in a clean, developer-focused UI with severity, confidence, file location, and review history.

## Features

- User Authentication — Register, login, and logout with JWT-based authentication.
- GitHub PR Review — Submit any valid public GitHub pull request URL to trigger analysis.
- AI + Baseline Analysis — Combines deterministic baseline security checks with Google's Gemini AI.
- Prioritized Findings — Includes severity, confidence, agent, file path, line number, and message.
- Review History — View past reviews, inspect details, and refresh on demand.
- Responsive UI — Modern React interface with dedicated Review History section.
- REST API — Django REST Framework backend with structured JSON and validation.
- Aggregation & Deduplication — Merges findings from multiple agents.

## Tech Stack

- Frontend: React 19, Vite, Axios, lucide-react
- Backend: Django, Django REST Framework, djangorestframework-simplejwt
- AI: Google Gemini API
- Integrations: GitHub REST API

## Project Structure

```
AI-Automated-Code-Review-System/
+-- backend/        # Django REST API, agents, AI reviewer, GitHub integration
+-- frontend/       # React + Vite frontend UI
+-- tests/          # Backend tests
+-- compose.yaml    # Docker Compose setup
+-- README.md
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+ (or compatible)
- npm

### Backend Setup

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Update `VITE_API_BASE_URL` in `frontend/.env` if your backend runs on a different host/port.

## Frontend Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run lint     # Run ESLint
npm run preview  # Preview production build
```

## API Overview

- POST /api/register/ — Create a new user account
- POST /api/login/ — Obtain JWT access/refresh tokens
- POST /api/review/ — Submit a GitHub PR URL for review (requires auth)
- GET /api/reviews/ — Fetch authenticated user's review history
- GET /api/reviews/<run_id>/ — Fetch detailed review with findings

## Development Notes

- Frontend is a single-page React app using Vite.
- All API calls use Axios with automatic JWT attachment via request interceptor.
- UI preserves existing behavior and API contracts.
- Lint and build must pass before committing changes.

## License

This project is for educational and development purposes.
