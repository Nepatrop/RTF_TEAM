from fastapi import status, HTTPException
from typing import List, Dict, Any
import httpx


class AgentService:
    def __init__(self, url: str):
        self.url = url

    async def health_check(self):
        http_exception = HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent service unavailable",
        )
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.url}/healthz")
                if response.status_code != 200:
                    raise http_exception
        except httpx.HTTPError:
            raise http_exception

    async def create_project(self, title: str, files_meta: List[dict]) -> Dict:
        multipart_files = []
        for meta in files_meta:
            try:
                f = open(meta["path"].lstrip("/"), "rb")
            except FileNotFoundError:
                raise HTTPException(500, f"File not found: {meta['path']}")
            multipart_files.append(("files", (meta["name"], f, meta["mime_type"])))

        data = {"title": title}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/api/v1/projects", data=data, files=multipart_files
                )
        finally:
            for _, (name, f, mime) in multipart_files:
                f.close()

        return response.json()

    async def delete_project(self, project_id: str) -> None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.url}/api/v1/projects/{project_id}"
                )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
            )
        data = response.json()
        if data.get("status") != "deleted":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Agent did not delete project: {data}",
            )
