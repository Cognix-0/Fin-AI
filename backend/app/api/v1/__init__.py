from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.expenses import router as expenses_router
from app.api.v1.meta import router as meta_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
for r in (auth_router, expenses_router, budgets_router, analytics_router, meta_router, users_router):
    api_router.include_router(r)
