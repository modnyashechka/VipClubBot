from aiogram import Router
from .admin import admin_router
from .games import games_router
from .common import common_router

# Główny agregator routerów systemu modularnego
main_router = Router()
main_router.include_router(admin_router)
main_router.include_router(games_router)
main_router.include_router(common_router)