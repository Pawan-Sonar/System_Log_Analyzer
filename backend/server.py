"""Security Log Analyzer - FastAPI entry point."""
from dotenv import load_dotenv
load_dotenv()

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

import auth as auth_mod
from routers import logs_router, analytics_router, alerts_router, reports_router, mitre_router, geo_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    app.state.mongo_client = client
    app.state.db = db

    # Indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.logs.create_index([("user_id", 1), ("timestamp", -1)])
    await db.logs.create_index("ip_address")
    await db.alerts.create_index([("user_id", 1), ("timestamp", -1)])
    await db.password_reset_tokens.create_index("token", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")

    # Seed admin
    await auth_mod.seed_admin(db)
    logger.info("Startup complete: %s", db_name)

    yield

    client.close()


app = FastAPI(title="Security Log Analyzer", lifespan=lifespan)

# CORS — Allow specific origin OR wildcard via env
cors_origins = os.environ.get("CORS_ORIGINS", "*")
origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
if origins == ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"service": "Security Log Analyzer", "status": "ok"}


@api_router.get("/health")
async def health():
    return {"status": "ok"}


api_router.include_router(auth_mod.router)
api_router.include_router(logs_router)
api_router.include_router(analytics_router)
api_router.include_router(alerts_router)
api_router.include_router(reports_router)
api_router.include_router(mitre_router)
api_router.include_router(geo_router)

app.include_router(api_router)
