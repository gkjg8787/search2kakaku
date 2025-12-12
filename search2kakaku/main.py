from contextlib import asynccontextmanager

from fastapi import FastAPI, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse


from routers.api import api_router
from routers.html.urls import router as html_router
from routers.html.kakaku import router as kakaku_router
from databases.sql.create_db import create_db
from common.logger_config import configure_logger

configure_logger(filename="app.log", logging_level="INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router)
app.include_router(html_router)
app.include_router(kakaku_router)


@app.get("/")
async def root(request: Request):
    return None
