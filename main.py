from fastapi import FastAPI
from api.question.routers.question import router as question_router
from api.grading.routers.subjective_grading import router as grading_router

app = FastAPI()

app.include_router(question_router)
app.include_router(grading_router)
