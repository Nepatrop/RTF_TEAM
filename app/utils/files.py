import os
from datetime import datetime

from fastapi import HTTPException, UploadFile, status
import aiofiles

from app.core.config import settings
from app.models import InterviewTypeEnum

files_dir = 'files'
upload_dir = 'upload'

MIME_TO_INTERVIEW = {
    # text
    "text/plain": InterviewTypeEnum.TEXT_FILE,
    "text/markdown": InterviewTypeEnum.TEXT_FILE,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": InterviewTypeEnum.TEXT_FILE,
    # audio
    "audio/mpeg": InterviewTypeEnum.AUDIO,
    "audio/wav": InterviewTypeEnum.AUDIO,
}
ALLOWED_EXTENSIONS = ['.txt', '.md', '.docx', '.mp3', '.wav']


async def save_file(file: UploadFile) -> str:

    directory = os.path.join(upload_dir, files_dir)
    os.makedirs(directory, exist_ok=True)

    current_date = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
    extension = file.filename.split(".")[-1]
    filename = f"{current_date}.{extension}"

    file_path = os.path.join(directory, filename)

    async with aiofiles.open(file_path, "wb") as buffer:
        content = await file.read()
        await buffer.write(content)

    return f"/{upload_dir}/{files_dir}/{filename}"


def get_type_by_file(file: UploadFile) -> InterviewTypeEnum:
    interview_type = MIME_TO_INTERVIEW.get(file.content_type)
    if not interview_type:
        allowed = ", ".join(ALLOWED_EXTENSIONS)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"File {file.filename} has invalid extension. Allowed: {allowed}")
    return interview_type
