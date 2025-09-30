"""FastAPI server exposing AI agent endpoints."""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from ai_agents.agents import AgentConfig, ChatAgent, SearchAgent
import random
from datetime import timedelta
import bcrypt
import jwt


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent


class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


class ChatRequest(BaseModel):
    message: str
    agent_type: str = "chat"
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    success: bool
    response: str
    agent_type: str
    capabilities: List[str]
    metadata: dict = Field(default_factory=dict)
    error: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


class SearchResponse(BaseModel):
    success: bool
    query: str
    summary: str
    search_results: Optional[dict] = None
    sources_count: int
    error: Optional[str] = None


# Auth Models
class UserSignup(BaseModel):
    email: str
    password: str
    username: str


class UserLogin(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    username: Optional[str] = None
    error: Optional[str] = None


# Staking Models
class StakingAsset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    asset_name: str
    asset_symbol: str
    amount_staked: float
    current_value: float
    apy: float
    rewards_earned: float
    staking_date: datetime
    logo_url: Optional[str] = None


class StakingOverview(BaseModel):
    total_staked_value: float
    total_rewards_earned: float
    average_apy: float
    total_assets: int
    performance_change_24h: float


class RewardHistory(BaseModel):
    date: str
    amount: float
    asset_symbol: str


class PerformanceData(BaseModel):
    date: str
    value: float


JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


def _ensure_db(request: Request):
    try:
        return request.app.state.db
    except AttributeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=503, detail="Database not ready") from exc


def _create_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        return None


def _get_user_from_token(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ")[1]
    payload = _verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload


def _generate_mock_staking_data(user_id: str) -> List[dict]:
    """Generate realistic mock staking data for a user."""
    assets = [
        {"name": "Ethereum", "symbol": "ETH", "logo": "https://images.unsplash.com/photo-1622630998477-20aa696ecb05?w=100"},
        {"name": "Polkadot", "symbol": "DOT", "logo": "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=100"},
        {"name": "Cardano", "symbol": "ADA", "logo": "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=100"},
        {"name": "Solana", "symbol": "SOL", "logo": "https://images.unsplash.com/photo-1639762681057-408e52192e55?w=100"},
        {"name": "Cosmos", "symbol": "ATOM", "logo": "https://images.unsplash.com/photo-1640826514546-7d2b75c88886?w=100"},
    ]

    staking_data = []
    for asset in assets:
        amount = random.uniform(10, 500)
        price = random.uniform(50, 3000)
        apy = random.uniform(4.5, 15.0)
        days_staked = random.randint(30, 365)

        staking_data.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "asset_name": asset["name"],
            "asset_symbol": asset["symbol"],
            "amount_staked": round(amount, 2),
            "current_value": round(amount * price, 2),
            "apy": round(apy, 2),
            "rewards_earned": round(amount * (apy / 100) * (days_staked / 365), 2),
            "staking_date": (datetime.now(timezone.utc) - timedelta(days=days_staked)).isoformat(),
            "logo_url": asset["logo"],
        })

    return staking_data


def _generate_rewards_history(days: int = 30) -> List[dict]:
    """Generate mock rewards history."""
    history = []
    assets = ["ETH", "DOT", "ADA", "SOL", "ATOM"]

    for i in range(days):
        date = datetime.now(timezone.utc) - timedelta(days=days - i)
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "amount": round(random.uniform(0.5, 5.0), 2),
            "asset_symbol": random.choice(assets),
        })

    return history


def _generate_performance_data(days: int = 30, start_value: float = 50000) -> List[dict]:
    """Generate mock performance data with realistic trends."""
    performance = []
    current_value = start_value

    for i in range(days):
        date = datetime.now(timezone.utc) - timedelta(days=days - i)
        # Add some volatility
        change = random.uniform(-0.02, 0.03)  # -2% to +3% daily change
        current_value *= (1 + change)

        performance.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": round(current_value, 2),
        })

    return performance


def _get_agent_cache(request: Request) -> Dict[str, object]:
    if not hasattr(request.app.state, "agent_cache"):
        request.app.state.agent_cache = {}
    return request.app.state.agent_cache


async def _get_or_create_agent(request: Request, agent_type: str):
    cache = _get_agent_cache(request)
    if agent_type in cache:
        return cache[agent_type]

    config: AgentConfig = request.app.state.agent_config

    if agent_type == "search":
        cache[agent_type] = SearchAgent(config)
    elif agent_type == "chat":
        cache[agent_type] = ChatAgent(config)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown agent type '{agent_type}'")

    return cache[agent_type]


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(ROOT_DIR / ".env")

    mongo_url = os.getenv("MONGO_URL")
    db_name = os.getenv("DB_NAME")

    if not mongo_url or not db_name:
        missing = [name for name, value in {"MONGO_URL": mongo_url, "DB_NAME": db_name}.items() if not value]
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    client = AsyncIOMotorClient(mongo_url)

    try:
        app.state.mongo_client = client
        app.state.db = client[db_name]
        app.state.agent_config = AgentConfig()
        app.state.agent_cache = {}
        logger.info("AI Agents API starting up")
        yield
    finally:
        client.close()
        logger.info("AI Agents API shutdown complete")


app = FastAPI(
    title="AI Agents API",
    description="Minimal AI Agents API with LangGraph and MCP support",
    lifespan=lifespan,
)

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate, request: Request):
    db = _ensure_db(request)
    status_obj = StatusCheck(**input.model_dump())
    await db.status_checks.insert_one(status_obj.model_dump())
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks(request: Request):
    db = _ensure_db(request)
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]


@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(chat_request: ChatRequest, request: Request):
    try:
        agent = await _get_or_create_agent(request, chat_request.agent_type)
        response = await agent.execute(chat_request.message)

        return ChatResponse(
            success=response.success,
            response=response.content,
            agent_type=chat_request.agent_type,
            capabilities=agent.get_capabilities(),
            metadata=response.metadata,
            error=response.error,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error in chat endpoint")
        return ChatResponse(
            success=False,
            response="",
            agent_type=chat_request.agent_type,
            capabilities=[],
            error=str(exc),
        )


@api_router.post("/search", response_model=SearchResponse)
async def search_and_summarize(search_request: SearchRequest, request: Request):
    try:
        search_agent = await _get_or_create_agent(request, "search")
        search_prompt = (
            f"Search for information about: {search_request.query}. "
            "Provide a comprehensive summary with key findings."
        )
        result = await search_agent.execute(search_prompt, use_tools=True)

        if result.success:
            metadata = result.metadata or {}
            return SearchResponse(
                success=True,
                query=search_request.query,
                summary=result.content,
                search_results=metadata,
                sources_count=int(metadata.get("tool_run_count", metadata.get("tools_used", 0)) or 0),
            )

        return SearchResponse(
            success=False,
            query=search_request.query,
            summary="",
            sources_count=0,
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error in search endpoint")
        return SearchResponse(
            success=False,
            query=search_request.query,
            summary="",
            sources_count=0,
            error=str(exc),
        )


@api_router.get("/agents/capabilities")
async def get_agent_capabilities(request: Request):
    try:
        search_agent = await _get_or_create_agent(request, "search")
        chat_agent = await _get_or_create_agent(request, "chat")

        return {
            "success": True,
            "capabilities": {
                "search_agent": search_agent.get_capabilities(),
                "chat_agent": chat_agent.get_capabilities(),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error getting capabilities")
        return {"success": False, "error": str(exc)}


# Authentication Endpoints
@api_router.post("/auth/signup", response_model=AuthResponse)
async def signup(user_data: UserSignup, request: Request):
    try:
        db = _ensure_db(request)

        # Check if user exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            return AuthResponse(success=False, error="Email already registered")

        # Hash password
        hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())

        # Create user
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": user_data.email,
            "username": user_data.username,
            "password": hashed_password.decode('utf-8'),
            "created_at": datetime.now(timezone.utc),
        }

        await db.users.insert_one(user)

        # Generate token
        token = _create_token(user_id, user_data.username)

        return AuthResponse(success=True, token=token, username=user_data.username)
    except Exception as exc:
        logger.exception("Error in signup")
        return AuthResponse(success=False, error=str(exc))


@api_router.post("/auth/login", response_model=AuthResponse)
async def login(credentials: UserLogin, request: Request):
    try:
        db = _ensure_db(request)

        # Find user
        user = await db.users.find_one({"email": credentials.email})
        if not user:
            return AuthResponse(success=False, error="Invalid email or password")

        # Verify password
        if not bcrypt.checkpw(credentials.password.encode('utf-8'), user["password"].encode('utf-8')):
            return AuthResponse(success=False, error="Invalid email or password")

        # Generate token
        token = _create_token(user["id"], user["username"])

        return AuthResponse(success=True, token=token, username=user["username"])
    except Exception as exc:
        logger.exception("Error in login")
        return AuthResponse(success=False, error=str(exc))


# Staking Endpoints
@api_router.get("/staking/overview")
async def get_staking_overview(request: Request):
    try:
        user = _get_user_from_token(request)
        db = _ensure_db(request)

        # Generate or fetch staking data
        staking_data = _generate_mock_staking_data(user["user_id"])

        # Calculate overview
        total_staked = sum(asset["current_value"] for asset in staking_data)
        total_rewards = sum(asset["rewards_earned"] for asset in staking_data)
        avg_apy = sum(asset["apy"] for asset in staking_data) / len(staking_data) if staking_data else 0

        # Generate performance change (mock)
        performance_change = random.uniform(-5.0, 8.0)

        return {
            "success": True,
            "data": {
                "total_staked_value": round(total_staked, 2),
                "total_rewards_earned": round(total_rewards, 2),
                "average_apy": round(avg_apy, 2),
                "total_assets": len(staking_data),
                "performance_change_24h": round(performance_change, 2),
            }
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in staking overview")
        raise HTTPException(status_code=500, detail=str(exc))


@api_router.get("/staking/assets")
async def get_staking_assets(request: Request):
    try:
        user = _get_user_from_token(request)

        # Generate mock staking data
        staking_data = _generate_mock_staking_data(user["user_id"])

        return {
            "success": True,
            "data": staking_data,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in staking assets")
        raise HTTPException(status_code=500, detail=str(exc))


@api_router.get("/staking/rewards-history")
async def get_rewards_history(request: Request, days: int = 30):
    try:
        user = _get_user_from_token(request)

        # Generate mock rewards history
        history = _generate_rewards_history(days)

        return {
            "success": True,
            "data": history,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in rewards history")
        raise HTTPException(status_code=500, detail=str(exc))


@api_router.get("/staking/performance")
async def get_performance_data(request: Request, days: int = 30):
    try:
        user = _get_user_from_token(request)

        # Generate mock performance data
        performance = _generate_performance_data(days)

        return {
            "success": True,
            "data": performance,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in performance data")
        raise HTTPException(status_code=500, detail=str(exc))


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
