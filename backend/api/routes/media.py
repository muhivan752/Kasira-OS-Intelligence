import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.staticfiles import StaticFiles

from backend.api.deps import get_current_user
from backend.models.user import User

router = APIRouter()

UPLOAD_DIR = "/app/uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE_MB = 5

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, detail=f"Format tidak didukung. Gunakan: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, detail=f"Ukuran file maksimal {MAX_SIZE_MB}MB")

    filename = f"{uuid.uuid4()}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/{filename}"}
