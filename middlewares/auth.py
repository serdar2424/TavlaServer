from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from jose import JWTError, jwt
from fastapi import HTTPException, status
from core.config import SECRET_KEY, ALGORITHM
from services.auth import oauth2_scheme

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Bypass authentication for specific routes
        if request.url.path in ["/register", "/token", "/password-recovery", "/password-reset", "/google-login", "/ws", "/docs", "/openapi.json"] or request.method == "OPTIONS":
            return await call_next(request)

        try:
            token = await oauth2_scheme(request)
        except HTTPException:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"},
            )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            request.state.user = payload.get("sub")
        except JWTError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Could not validate credentials"},
            )
        response = await call_next(request)
        return response