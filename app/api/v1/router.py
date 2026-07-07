"""Agrega todos os routers da v1 sob um único APIRouter."""

from fastapi import APIRouter

from . import auth, benchmark, classify, comparability, meta, tenders

api_router = APIRouter()
api_router.include_router(meta.router)
api_router.include_router(auth.router)
api_router.include_router(classify.router)
api_router.include_router(benchmark.router)
api_router.include_router(comparability.router)
api_router.include_router(tenders.router)
