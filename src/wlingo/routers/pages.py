import os
import uuid

from fastapi import APIRouter, Cookie
from fastapi.responses import FileResponse, HTMLResponse

from ..config import settings

router = APIRouter()

_USER_COOKIE = "wlingo_user_id"
_USER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 5  # 5 years


@router.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(
    full_path: str,
    wlingo_user_id: str | None = Cookie(default=None),
):
    index_path = os.path.join(settings.STATIC_DIR, "index.html")
    resp: FileResponse | HTMLResponse
    if os.path.exists(index_path):
        resp = FileResponse(index_path)
    else:
        resp = HTMLResponse("<div id='root'></div>")

    if not wlingo_user_id:
        resp.set_cookie(
            key=_USER_COOKIE,
            value=str(uuid.uuid4()),
            max_age=_USER_COOKIE_MAX_AGE,
            httponly=True,
        )
    return resp
