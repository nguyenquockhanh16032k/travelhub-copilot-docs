import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.tour_bulk import router as tour_bulk_router
from app.api.v1.customers import router as customers_router
from app.api.v1.bookings import router as bookings_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.itineraries import router as itineraries_router
from app.api.v1.operations import router as operations_router
from app.api.v1.suppliers_expenses import router as suppliers_expenses_router
from app.api.v1.content import router as content_router
from app.api.v1.reports import router as reports_router
from app.api.v1.users import router as users_router
from app.db.session import SessionLocal
from app.services.booking_service import expire_pending_bookings


async def _booking_expiration_worker() -> None:
    while True:
        with SessionLocal() as db:
            expire_pending_bookings(db)
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(_: FastAPI):
    worker = asyncio.create_task(_booking_expiration_worker())
    try:
        yield
    finally:
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)

app = FastAPI(
    title="TravelHub API",
    version="0.1.0",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(tour_bulk_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(bookings_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(itineraries_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(suppliers_expenses_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
