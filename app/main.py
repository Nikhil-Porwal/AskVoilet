from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints, auth  # Import both routers
from app.db.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing database...")
    init_db()
    print("Database initialized.")
    yield

app = FastAPI(title="AskVoilet", lifespan=lifespan)

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

app.include_router(endpoints.router, prefix="/api/app", tags=["Application"])


@app.get("/")
async def read_root():
    return {"message": "If it is your wish, I will travel anywhere to meet you. I am an Auto Memories Doll, my name is Violet Evergarden💜."}
