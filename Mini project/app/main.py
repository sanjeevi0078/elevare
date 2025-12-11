from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI(title="Elevare", description="AI-Powered Startup Launchpad")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/intake", response_class=HTMLResponse)
async def intake(request: Request):
    return templates.TemplateResponse("intake.html", {"request": request})

@app.get("/roadmap", response_class=HTMLResponse)
async def roadmap(request: Request):
    return templates.TemplateResponse("roadmap.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/user", response_class=HTMLResponse)
async def user(request: Request):
    return templates.TemplateResponse("user.html", {"request": request})

@app.get("/cofounder", response_class=HTMLResponse)
async def cofounder(request: Request):
    return templates.TemplateResponse("cofounder.html", {"request": request})

@app.get("/profile-setup", response_class=HTMLResponse)
async def profile_setup(request: Request):
    return templates.TemplateResponse("profile-setup.html", {"request": request})

@app.get("/features", response_class=HTMLResponse)
async def features(request: Request):
    return templates.TemplateResponse("features.html", {"request": request})

@app.get("/events", response_class=HTMLResponse)
async def events(request: Request):
    return templates.TemplateResponse("events.html", {"request": request})

@app.get("/mentorship", response_class=HTMLResponse)
async def mentorship(request: Request):
    return templates.TemplateResponse("mentorship.html", {"request": request})

@app.get("/idea-wall", response_class=HTMLResponse)
async def idea_wall(request: Request):
    return templates.TemplateResponse("idea-wall.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)