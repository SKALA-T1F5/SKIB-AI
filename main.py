from fastapi import FastAPI
from api.question.routers.question import router

app = FastAPI()

app.include_router(router)