from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import auth, users, admin, movies, comments, moderator
from src.database import engine, Base
from src.config import get_settings

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Online Cinema API",
    description="API for online cinema platform with user authentication and authorization",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(movies.router)
app.include_router(comments.router)
app.include_router(moderator.router)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Online Cinema API",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
