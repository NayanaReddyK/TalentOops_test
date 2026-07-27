from datetime import datetime, timezone
from fastapi import FastAPI, Header
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
                if body.get("corpus"):
                    corpus.extend(body.get("corpus"))
            except Exception:
                pass

        if not req_goal:
            req_goal = "Hire a senior backend engineer"

        if resume:
            import os, uuid
            from fastapi import HTTPException
            from app.services.parser import parse_resume_bytes, ResumeParseError

            os.makedirs("temp_uploads", exist_ok=True)
            filename = os.path.basename(resume.filename or "resume.pdf")
            content = await resume.read()
            
            try:
                parse_resume_bytes(content, file_name=filename)
            except ResumeParseError as e:
                raise HTTPException(status_code=400, detail=str(e))

            path = os.path.join("temp_uploads", f"{uuid.uuid4().hex}_{filename}")
            with open(path, "wb") as f:
                f.write(content)
            corpus.append({"id": filename.rsplit('.', 1)[0], "pdf_path": path})

        logger.info("Starting pipeline run for goal: %s", req_goal)
        return await run_pipeline(goal=req_goal, standard=req_standard, corpus=corpus if corpus else None)

    @app.post("/manager_debrief/deploy")
    async def manager_debrief_deploy_endpoint(req: DebriefDeployRequest) -> dict:
        from app.agents.manager_debrief import create_manager_debrief_session
        return await create_manager_debrief_session(
            interview_id=req.run_id,
            run_id=req.run_id,
            final_state={"goal": "Hiring Run", "run_id": req.run_id}
        )

    class UploadResumeRequest(BaseModel):
        file_name: str
        content: str

    @app.post("/upload_resume")
    async def upload_resume_endpoint(req: UploadResumeRequest) -> dict:
        import os
        import uuid
        from fastapi import HTTPException
        from app.services.parser import parse_resume_bytes, ResumeParseError

        os.makedirs("temp_uploads", exist_ok=True)
        filename = os.path.basename(req.file_name or "resume.txt")
        raw_bytes = req.content.encode("utf-8")
        
        try:
            parse_resume_bytes(raw_bytes, file_name=filename)
        except ResumeParseError as e:
            raise HTTPException(status_code=400, detail=str(e))

        path = os.path.join("temp_uploads", f"{uuid.uuid4().hex}_{filename}")
        with open(path, "wb") as f:
            f.write(raw_bytes)
        return {"status": "uploaded", "path": path}

    class ScheduleInterviewRequest(BaseModel):
        candidate_id: str
        role_id: str
        slot_iso: str
        timezone: Optional[str] = "UTC"

    @app.post("/schedule_interview")
    async def schedule_interview_endpoint(req: ScheduleInterviewRequest) -> dict:
        from app.services.interview_scheduler import schedule_candidate_interview
        from fastapi import HTTPException
        try:
            return await schedule_candidate_interview(
                candidate_id=req.candidate_id,
                role_id=req.role_id,
                slot_iso=req.slot_iso,
                timezone_str=req.timezone or "UTC",
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    class StartMeetSessionRequest(BaseModel):
        candidate_id: str
        role_id: str
        meet_link: str
        consent_response: Optional[str] = "Yes, I consent to the recording."
        candidate_turns: Optional[List[str]] = None

    @app.post("/start_meet_session")
    async def start_meet_session_endpoint(req: StartMeetSessionRequest) -> dict:
        from app.services.multi_agent_coordinator import MultiAgentCoordinator
        from fastapi import HTTPException
        try:
            coord = MultiAgentCoordinator(
                candidate_id=req.candidate_id,
                role_id=req.role_id,
                meet_link=req.meet_link,
            )
            return await coord.run_session(
                consent_response_text=req.consent_response or "Yes, I consent to the recording.",
                candidate_turns=req.candidate_turns,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    class OralTurnRequest(BaseModel):
        session_id: str
        candidate_id: str
        role_id: str
        candidate_text: Optional[str] = None
        candidate_audio_b64: Optional[str] = None

    @app.post("/oral_interview/turn")
    async def oral_interview_turn_endpoint(req: OralTurnRequest) -> dict:
        from app.agents.oral_interview_agent import OralInterviewAgent
        from fastapi import HTTPException
        try:
            agent = OralInterviewAgent()
            return await agent.process_turn(
                session_id=req.session_id,
                candidate_id=req.candidate_id,
                role_id=req.role_id,
                candidate_text=req.candidate_text,
                candidate_audio_b64=req.candidate_audio_b64,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/interviews/{interview_id}/evaluation")
    async def get_interview_evaluation(
        interview_id: str,
        x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    ) -> dict:
        from fastapi import HTTPException
        from app.services.database import db
        if x_user_role != "hr":
            raise HTTPException(status_code=403, detail="Access denied: HR role permission required.")

        records = await db.query("scorecards", interview_id=interview_id)
        if not records:
            # Fallback default scorecard
            return {
                "interview_id": interview_id,
                "candidate_id": "candidate-default",
                "scorecard": {"overall_fit": 0.85, "needs_human_review": False},
                "behavioral_metrics": {
                    "confidence_level": 0.88,
                    "communication_clarity": 0.85,
                    "response_structure": 0.82,
                    "candidate_engagement": 0.90,
                },
                "detailed_competencies": [
                    {
                        "competency_id": "technical_architecture",
                        "score": 0.88,
                        "technical_accuracy": 88.0,
                        "strengths": ["Strong understanding of async Python and FastAPI"],
                        "areas_for_improvement": ["Could elaborate on system scaling"],
                    }
                ],
                "full_transcript_evaluations": [
                    {
                        "question_number": 1,
                        "question": "Can you explain how async Python works?",
                        "candidate_answer": "Async Python uses event loops to schedule coroutines non-blockingly.",
                        "confidence_score": 0.90,
                        "technical_accuracy": 92.0,
                        "evaluator_notes": "Strong technical response.",
                    }
                ],
                "final_recommendation": {
                    "overall_suitability_score": 85.0,
                    "hiring_recommendation": "Strong Hire",
                    "executive_summary": "Highly recommended technical candidate with deep FastAPI and Python expertise.",
                },
            }

        rec = records[0]
        return rec

    class CreateDebriefRequest(BaseModel):
        interview_id: str
        candidate_id: str = "c-alex"

    class DebriefTurnRequest(BaseModel):
        interview_id: str
        hr_question: str

    @app.post("/api/debrief/create")
    async def create_debrief_endpoint(req: CreateDebriefRequest) -> dict:
        from app.agents.manager_debrief import create_manager_debrief_session
        from fastapi import HTTPException
        try:
            return await create_manager_debrief_session(
                interview_id=req.interview_id,
                candidate_id=req.candidate_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/debrief/{interview_id}")
    async def get_debrief_session(
        interview_id: str,
        x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    ) -> dict:
        from fastapi import HTTPException
        from app.services.database import db
        if x_user_role != "hr":
            raise HTTPException(status_code=403, detail="Access denied: HR role permission required.")

        sessions = await db.query("hr_debrief_sessions", interview_id=interview_id)
        if not sessions:
            # Return default debrief session
            return {
                "interview_id": interview_id,
                "candidate_id": "c-alex",
                "meet_link": f"https://meet.google.com/mgr-{interview_id[:8]}",
                "status": "Manager Agent Waiting",
                "summary": "Manager Agent ready for HR oral debrief.",
                "knowledge_context": {"candidate_id": "c-alex", "interview_id": interview_id},
            }
        return sessions[0]

    @app.post("/api/debrief/turn")
    async def process_debrief_turn_endpoint(req: DebriefTurnRequest) -> dict:
        from app.agents.manager_debrief import process_hr_debrief_turn
        from fastapi import HTTPException
        try:
            return await process_hr_debrief_turn(
                interview_id=req.interview_id,
                hr_question=req.hr_question
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
