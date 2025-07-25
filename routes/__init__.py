from .auth import router as auth_router
from .users import router as users_router
from .invites import router as invites_router
from .game import router as game_router
from .tournaments import router as tournaments_router

routers = [auth_router, users_router, game_router, invites_router, tournaments_router]