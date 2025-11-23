from fastapi import status, UploadFile, HTTPException
from typing import Optional

MAX_IMAGE_SIZE = 25 * 1024 * 1024

async def get_file(file: Optional[UploadFile] = None) -> Optional[UploadFile]:
    if file is None:
        return None

    if file.size > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is too large")

    return file
