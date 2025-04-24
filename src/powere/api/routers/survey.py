from fastapi import APIRouter

router = APIRouter(
    prefix="/survey",
    tags=["survey"],
)