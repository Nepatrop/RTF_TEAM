import os
from datetime import datetime

from fastapi import UploadFile
import aiofiles
import mimetypes

files_dir = "files"
upload_dir = "upload"


async def save_file_with_meta(file: UploadFile):
    directory = os.path.join(upload_dir, files_dir)
    os.makedirs(directory, exist_ok=True)

    current_date = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
    extension = file.filename.split(".")[-1]
    filename = f"{current_date}.{extension}"

    mime_type, _ = mimetypes.guess_type(file.filename)
    file_path = os.path.join(directory, filename)

    async with aiofiles.open(file_path, "wb") as buffer:
        content = await file.read()
        await buffer.write(content)

    return {
        "name": file.filename,
        "path": f"/{upload_dir}/{files_dir}/{filename}",
        "size": file.size,
        "mime_type": mime_type,
    }
