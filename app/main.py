from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    from app.services.logging import (
        configure_logging,
        RequestLoggingMiddleware,
        ErrorLoggingMiddleware,
        get_logger
    )

    # Configure logging
    logger = configure_logging()
    logger.info("Creating TalentOps application")

    app = FastAPI(title="TalentOps")

    # Apply middleware for CORS, gzip compression, and logging
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Add logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorLoggingMiddleware)

    logger.info("Application middleware configured")

    from fastapi import Request, Form, File, UploadFile
    from pydantic import BaseModel
    from typing import Optional, List, Dict, Any

    @app.get("/health")
    async def health() -> dict:
        """Health check endpoint."""
        logger.info("Health check requested")
        from app.graph.state import SUB_AGENTS
        nodes = ["manager"] + SUB_AGENTS
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "supabase_configured": settings.supabase_configured,
            "nodes": nodes,
            "supervisor_nodes": nodes,
        }

    @app.get("/outbox")
    async def outbox_endpoint() -> dict:
        from app.agents.email_client import get_mock_outbox
        return {"emails": [msg.__dict__ for msg in get_mock_outbox()]}

    class RunRequest(BaseModel):
        goal: str
        standard: Optional[str] = None
        drive_url: Optional[str] = None
        corpus: Optional[List[Dict[str, Any]]] = None

    class EmailQueryRequest(BaseModel):
        role_id: str
        from_email: str
        subject: Optional[str] = ""

    class DebriefDeployRequest(BaseModel):
        run_id: str
        meet_link: Optional[str] = None

    @app.post("/run")
    async def run_pipeline_endpoint(
        request: Request,
        goal: Optional[str] = Form(None),
        standard: Optional[str] = Form(None),
        drive_url: Optional[str] = Form(None),
        resume: Optional[UploadFile] = File(None),
    ) -> dict:
        from app.graph.supervisor import run_pipeline
        corpus = []
        req_goal = goal
        req_standard = standard

        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body = await request.json()
                req_goal = body.get("goal")
                req_standard = body.get("standard")
                req_drive = body.get("drive_url")
                if req_drive:
                    corpus.append({"drive_url": req_drive})
                if body.get("corpus"):
                    corpus.extend(body.get("corpus"))
            except Exception:
                pass

        if drive_url:
            corpus.append({"drive_url": drive_url})

        if not req_goal:
            req_goal = "Hire a senior backend engineer"

        if resume:
            import os, uuid
            os.makedirs("temp_uploads", exist_ok=True)
            filename = resume.filename or "resume.pdf"
            path = os.path.join("temp_uploads", f"{uuid.uuid4().hex}_{filename}")
            content = await resume.read()
            with open(path, "wb") as f:
                f.write(content)
            corpus.append({"id": filename.split('.')[0], "pdf_path": path})

        logger.info("Starting pipeline run for goal: %s", req_goal)
        return await run_pipeline(goal=req_goal, standard=req_standard, corpus=corpus if corpus else None)

    @app.post("/manager_debrief/deploy")
    async def manager_debrief_deploy_endpoint(req: DebriefDeployRequest) -> dict:
        from app.agents.manager_debrief import create_manager_debrief_session
        return await create_manager_debrief_session(req.run_id, {"goal": "Hiring Run", "run_id": req.run_id})

    @app.post("/upload_resume")
    async def upload_resume_endpoint(file_name: str, content: str) -> dict:
        import os
        import uuid
        os.makedirs("temp_uploads", exist_ok=True)
        path = os.path.join("temp_uploads", f"{uuid.uuid4().hex}_{file_name}")
        with open(path, "w") as f:
            f.write(content)
        return {"status": "uploaded", "path": path}

    @app.post("/query_email")
    async def query_email_endpoint(req: EmailQueryRequest) -> dict:
        from app.services.email_handler import handle_incoming_email
        payload = {"role_id": req.role_id, "from": req.from_email, "subject": req.subject or ""}
        return await handle_incoming_email(payload)

    for name in ("webhooks", "fairness", "interviews"):
        try:
            module = __import__(f"app.api.routes.{name}", fromlist=["router"])
            app.include_router(module.router)
        except ImportError:
            pass

    try:
        from app.services.audio_bridge import ws_endpoint
        from fastapi import WebSocket, status

        @app.websocket("/ws/audio/{meeting_id}")
        async def audio_ws(websocket: WebSocket, meeting_id: str) -> None:
            await ws_endpoint(websocket, meeting_id)
            
        @app.websocket("/ws/audio")
        async def audio_ws_fallback(websocket: WebSocket) -> None:
            # Query param fallback (e.g. ?meeting_id=xxx or ?interview_id=xxx)
            meeting_id = websocket.query_params.get("meeting_id") or websocket.query_params.get("interview_id")
            if not meeting_id:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Meeting ID or Interview ID required")
                return
            await ws_endpoint(websocket, meeting_id)
    except ImportError:
        pass



    return app


app = create_app()
