from fastapi import FastAPI
from api.question.routers.question import router as question_router

app = FastAPI()

app.include_router(question_router)
