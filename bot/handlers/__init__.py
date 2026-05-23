"""
bot/handlers/__init__.py — Register all routers into a single list.
"""
from bot.handlers.start import router as start_router
from bot.handlers.status import router as status_router
from bot.handlers.nb import router as nb_router
from bot.handlers.deadlines import router as deadlines_router

all_routers = [
    start_router,
    status_router,
    nb_router,
    deadlines_router,
]
