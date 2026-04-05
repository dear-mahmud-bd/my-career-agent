from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.logger import logger
from app.core.security import verify_credentials
from app.db.init_db import init_db
from app.api.v1.router import router


# ─────────────────────────────
# Startup / Shutdown
# ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}...")

    # Init database
    await init_db()
    logger.success("Database ready ✅")

    # Start continuous scan loop
    from app.core.scan_manager import scan_manager
    scan_manager.start()
    logger.success("Scan manager started ✅")

    yield

    # Shutdown
    logger.info("Shutting down...")
    scan_manager.stop()


# ─────────────────────────────
# App instance
# ─────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# ─────────────────────────────
# Middleware
# ─────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=86400,  # 24 hours
)

# ─────────────────────────────
# Static files + Templates
# ─────────────────────────────
app.mount(
    "/static",
    StaticFiles(directory="app/ui/static"),
    name="static",
)

templates = Jinja2Templates(directory="app/ui/templates")


# ─────────────────────────────
# Auth routes
# ─────────────────────────────
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    if request.session.get("authenticated"):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error},
    )


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if verify_credentials(username, password):
        request.session["authenticated"] = True
        request.session["username"] = username
        logger.info(f"User '{username}' logged in")
        return RedirectResponse(url="/dashboard", status_code=303)

    logger.warning(f"Failed login attempt for '{username}'")
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "Invalid username or password",
        },
        status_code=401,
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")


# ─────────────────────────────
# Root redirect
# ─────────────────────────────
@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")


# ─────────────────────────────
# Include all routes
# ─────────────────────────────
app.include_router(router)


# ─────────────────────────────
# Health check
# ─────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }