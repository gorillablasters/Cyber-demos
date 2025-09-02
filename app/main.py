from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import profiles, accounts, transactions, analytics

app = FastAPI(title="WINNIE API", version="1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profiles.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(analytics.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
