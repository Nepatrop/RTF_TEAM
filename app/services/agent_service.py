from fastapi import status, HTTPException
from typing import List, Dict, Any, Optional
import httpx
import uuid

from app import schemas


class AgentService:
    def __init__(
        self,
        url: str,
        callback_url: str,
    ):
        self.url = url
        self.callback_url = callback_url

    async def health_check(self):
        http_exception = HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent service unavailable",
        )
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.url}/health")
                if response.status_code != 200:
                    raise http_exception
        except httpx.HTTPError:
            raise http_exception

    async def create_project(
        self, title: str, description: str, files_meta: List[dict]
    ) -> Dict:
        multipart_files = []
        for meta in files_meta:
            try:
                f = open(meta["path"].lstrip("/"), "rb")
            except FileNotFoundError:
                raise HTTPException(500, f"File not found: {meta['path']}")
            multipart_files.append(("files", (meta["name"], f, meta["mime_type"])))

        x_request_id = str(uuid.uuid4())
        data = {
            "title": title,
            "description": description,
            "callback_url": self.callback_url,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/projects",
                    headers={"X-Request-ID": x_request_id},
                    data=data,
                    files=multipart_files,
                )
        finally:
            for _, (name, f, mime) in multipart_files:
                f.close()

        return response.json()

    async def delete_project(self, project_id: str) -> None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"{self.url}/projects/{project_id}")
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

    async def add_files_to_project(
        self, project_id: str, files_meta: List[dict]
    ) -> Dict:
        multipart_files = []
        for meta in files_meta:
            try:
                f = open(meta["path"].lstrip("/"), "rb")
            except FileNotFoundError:
                raise HTTPException(500, f"File not found: {meta['path']}")
            multipart_files.append(("files", (meta["name"], f, meta["mime_type"])))

        x_request_id = str(uuid.uuid4())
        data = {"callback_url": self.callback_url}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/projects/{project_id}",
                    headers={"X-Request-ID": x_request_id},
                    data=data,
                    files=multipart_files,
                )
        finally:
            for _, (name, f, mime) in multipart_files:
                f.close()

        return response.json()

    async def create_session_on_project(
        self,
        project_id: int,
        user_goal: str,
    ) -> Dict:
        x_request_id = str(uuid.uuid4())
        data = {
            "project_id": project_id,
            "user_goal": user_goal,
            "callback_url": self.callback_url,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/interview-session",
                    json=data,
                    headers={"X-Request-ID": x_request_id},
                )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
            )
        return response.json()

    async def create_interview_session_on_context(
        self,
        context_questions: schemas.ContextQuestion,
        user_goal: str,
    ) -> Dict:
        x_request_id = str(uuid.uuid4())
        data = {
            "user_goal": user_goal,
            "callback_url": self.callback_url,
            "context_questions": [
                {"task": context_questions.task},
                {"goal": context_questions.goal},
                {"value": context_questions.value},
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/interview-session",
                    json=data,
                    headers={"X-Request-ID": x_request_id},
                )
                if response.status_code != 202:
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
        x_request_id = str(uuid.uuid4())
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.url}/interview-session/{session_id}",
                    headers={"X-Request-ID": x_request_id},
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

    async def submit_text_answer(
        self, session_id: str, question_id: str, answer: str, is_skipped: bool
    ) -> Dict:
        data = {
            "answers": answer,
            "is_skipped": is_skipped,
            "callback_url": self.callback_url,
        }
        x_request_id = str(uuid.uuid4())
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/interview-session/{session_id}/answer/{question_id}",
                    json=data,
                    headers={"X-Request-ID": x_request_id},
                )
                if response.status_code != 202:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to submit answer",
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
                    f"{self.url}/interview-session/{session_id}/cancel"
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
