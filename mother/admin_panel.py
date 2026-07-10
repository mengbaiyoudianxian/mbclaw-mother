from fastapi import APIRouter
from fastapi.responses import RedirectResponse
router = APIRouter()

@router.get("/admin")
def admin_redirect():
    return RedirectResponse("http://8.147.69.152:8001/admin", status_code=302)
