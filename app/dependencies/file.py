from fastapi import status, UploadFile, HTTPException, Depends
from typing import List

MAX_FILE_SIZE = 25 * 1024 * 1024
AUDIO_ALLOWED = {".mp3", ".wav", ".ogg", ".m4a"}
TEXT_ALLOWED = {".txt", ".md", ".docx"}


async def get_files(files: List[UploadFile] = None) -> List[UploadFile]:
    for file in files:
        if file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is too large",
            )
    return files


async def get_audio_files(
    files: List[UploadFile] = Depends(get_files),
) -> List[UploadFile]:
    for file in files:
        ext = "." + file.filename.lower().split(".")[-1]
        if ext not in AUDIO_ALLOWED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not a supported audio file",
            )
    return files


async def get_text_files(
    files: List[UploadFile] = Depends(get_files),
) -> List[UploadFile]:
    for f in files:
        ext = "." + f.filename.lower().split(".")[-1]
        if ext not in TEXT_ALLOWED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {f.filename} is not a supported text file",
            )
    return files
