from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return request.app.state.templates.TemplateResponse(request, "home.html", {})
