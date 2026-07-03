import logging
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config import settings
from ..globals import templates
from ..models import SessionData
from .deps import get_active_session, get_user_id

router = APIRouter()
logger = logging.getLogger("wlingo")


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    user_id: str | None = Depends(get_user_id),
):
    resp = templates.TemplateResponse(request, "start.html")
    if not user_id:
        resp.set_cookie(
            key=settings.USER_COOKIE_NAME,
            value=str(uuid.uuid4()),
            httponly=True,
            samesite="Lax",
            max_age=settings.USER_STATS_TTL_DAYS * 86400,
        )
    return resp


@router.get("/quiz/{index}", response_class=HTMLResponse)
def display_question_page(
    request: Request,
    index: int,
    session_data: SessionData | None = Depends(get_active_session),
):
    if not session_data:
        return RedirectResponse(url="/", status_code=302)
    if index < 0 or index >= session_data.total_questions:
        return RedirectResponse(url="/result", status_code=302)
    return templates.TemplateResponse(
        request,
        "quiz.html",
        {
            "current_index": index,
            "mode": session_data.mode,
            "topic": session_data.topic,
        },
    )


@router.get("/result", response_class=HTMLResponse)
async def result_page(request: Request):
    return templates.TemplateResponse(request, "result.html")
