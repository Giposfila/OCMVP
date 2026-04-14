from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import engine, Base

app = FastAPI(title="VerifyAI")

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

Base.metadata.create_all(bind=engine)

from app.routers import pages, claims, auth

app.include_router(pages.router)
app.include_router(claims.router)
app.include_router(auth.router, prefix="")


@app.get("/health")
async def health():
    return {"status": "ok"}
