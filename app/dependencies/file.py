from fastapi import status, UploadFile, HTTPException, Depends, File
from typing import List, Optional

MAX_FILE_SIZE = 25 * 1024 * 1024
AUDIO_ALLOWED = {".mp3", ".wav", ".ogg", ".m4a"}
TEXT_ALLOWED = {".txt", ".md", ".docx"}


async def get_files(files: Optional[List[UploadFile]] = File(None)) -> List[UploadFile]:
    if not files:
        return []
    for file in files:
        if file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is too large",
            )
    return files


async def get_text_files(
    files: List[UploadFile] = Depends(get_files),
) -> List[UploadFile]:
    if not files:
        return []
    for f in files:
        ext = "." + f.filename.lower().split(".")[-1]
        if ext not in TEXT_ALLOWED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {f.filename} is not a supported text file",
            )
    return files
