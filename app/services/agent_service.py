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

    async def create_interview_session(self, project_id: str, questions: List) -> Dict:

        context_questions = {
            "task": questions[0],
            "goal": questions[1],
            "value": questions[2],
        }
        data = {
            "project_id": project_id,
            "context_questions": context_questions,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/api/v1/interview-session", json=data
                )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Agent failed to create session: {response.text}",
                    )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
            )
        return response.json()

    async def get_session_status(self, session_id: str) -> Dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.url}/api/v1/interview-session/{session_id}"
                )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to get session status",
                    )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
            )
        return response.json()

    async def submit_answers(
        self, session_id: str, iteration_number: str, answers: str
    ) -> Dict:
        data = {"answers": answers}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/api/v1/interview-session/{session_id}/{iteration_number}/answers",
                    json=data,
                )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to submit answers",
                    )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
            )
        return response.json()

    async def cancel_session(self, session_id: str) -> Dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/api/v1/interview-session/{session_id}/cancel"
                )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to cancel session",
                    )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
            )
        return response.json()
