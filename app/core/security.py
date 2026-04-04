from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from app.core.config import settings


def check_auth(request: Request) -> bool:
    """Check if user is authenticated via session."""
    return request.session.get("authenticated", False)


def require_auth(request: Request):
    """Redirect to login if not authenticated."""
    if not check_auth(request):
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
        )


def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password against .env values."""
    return (
        username == settings.ui_username
        and password == settings.ui_password
    )