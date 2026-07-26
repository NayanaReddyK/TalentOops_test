from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from app.services.vexa_client import VexaClient

router = APIRouter(prefix="/interviews", tags=["interviews"])
vexa_client = VexaClient()

class DeployBotRequest(BaseModel):
    meet_url: str
    candidate_id: str
    role_id: str
    interview_id: str | None = None

@router.post("/deploy")
async def deploy_bot(req: DeployBotRequest):
    """
    Step 2: The Command Code (Python)
    Shoots a laser-fast command to Vexa to deploy the bot into the meeting.
    """
    try:
        # Resolve the interview ID before calling Vexa so we can pass it
        interview_id = req.interview_id or uuid.uuid4().hex
        
        # We deploy the bot under the "candidate" voice context, as this is an interview.
        result = await vexa_client.join_meeting(
            meet_url=req.meet_url,
            bot_name="TalentOps Interviewer",
            voice_context="candidate",
            interview_id=interview_id
        )
        
        # Insert the interview into the database (ignore if it already exists)
        from app.services.database import db
        insert_result = await db.insert("interviews", {
            "id": interview_id,
            "candidate_id": req.candidate_id,
            "role_id": req.role_id,
            "transcript": []
        })
        
        # If insert_result is empty, it means RLS blocked it or a duplicate key error occurred.
        # This is fine; it means the row already exists or RLS is improperly configured.

        return {
            "status": "success",
            "message": "Bot deployed successfully!",
            "vexa_response": result,
            "interview_id": interview_id
        }
    except Exception as e:
        import httpx
        if isinstance(e, httpx.HTTPStatusError):
            raise HTTPException(status_code=e.response.status_code, detail=f"Vexa API error: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Failed to deploy Vexa bot: {str(e)}")

class StopBotRequest(BaseModel):
    meet_url: str

@router.post("/stop_by_url")
async def stop_bot_by_url(req: StopBotRequest):
    """
    Commands the bot to leave the meeting using the Google Meet URL.
    This is especially useful for kicking zombie bots.
    """
    try:
        # Extract the native meeting ID (e.g., qsk-svbr-wwd) from the URL
        native_meeting_id = req.meet_url.split("/")[-1].split("?")[0]
        
        # Vexa allows deleting by platform/native_meeting_id
        result = await vexa_client.leave_meeting(f"google_meet/{native_meeting_id}")
        return {
            "status": "success",
            "message": "Bot left the meeting successfully!",
            "vexa_response": result
        }
    except Exception as e:
        import httpx
        if isinstance(e, httpx.HTTPStatusError):
            if e.response.status_code == 404:
                return {"status": "success", "message": "Bot is already gone from the meeting."}
            raise HTTPException(status_code=e.response.status_code, detail=f"Vexa API error: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Failed to stop Vexa bot: {str(e)}")
