# Elevare - AI-Powered Startup Launchpad

A FastAPI-based platform that helps entrepreneurs refine their ideas, find cofounders, and build roadmaps for success.

## Project Structure

```
Mini project/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css   # Main stylesheet
│   │   └── js/              # JavaScript files
│   └── templates/           # HTML templates
│       ├── index.html       # Landing page
│       ├── login.html       # Authentication
│       ├── intake.html      # Idea submission
│       ├── roadmap.html     # Development roadmap
│       ├── dashboard.html   # User dashboard
│       ├── user.html        # User profile
│       ├── cofounder.html   # Cofounder matching
│       └── ...              # Other pages
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
└── README.md               # This file
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. Open your browser and navigate to:
```
http://localhost:8000
```

## Features

- **Idea Refinement**: AI-powered idea analysis and improvement
- **Cofounder Matching**: Smart matching algorithms for team building
- **Development Roadmap**: Interactive progress tracking
- **User Dashboard**: Personalized user experience
- **Responsive Design**: Mobile-first approach with modern UI

## API Endpoints

- `GET /` - Landing page
- `GET /login` - Authentication page
- `GET /intake` - Idea submission form
- `GET /roadmap` - Development roadmap
- `GET /dashboard` - User dashboard
- `GET /user` - User profile
- `GET /cofounder` - Cofounder matching

## Technology Stack

- **Backend**: FastAPI, Python
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling**: Tailwind CSS
- **Animations**: GSAP
- **Icons**: Font Awesome
- **Fonts**: Inter, Space Grotesk