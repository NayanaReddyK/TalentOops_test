import sys
with open('app/main.py', 'a', encoding='utf-8') as f:
    f.write('''

@app.get("/api/history")
async def get_history():
    \"\"\"Return a list of all candidates and their evaluations for the History UI.\"\"\"
    try:
        from app.services.database import db
        candidates = await db.query("candidates")
        scorecards = await db.query("scorecards")
        
        cand_map = {}
        for c in candidates:
            c_id = c.get("id") or c.get("candidate_id")
            if c_id:
                cand_map[c_id] = c
                
        score_map = {}
        for s in scorecards:
            c_id = s.get("candidate_id")
            if c_id:
                score_map[c_id] = s
                
        history = []
        for c_id, c in cand_map.items():
            s = score_map.get(c_id, {})
            scorecard_body = s.get("scorecard", {}) or {}
            rec_body = s.get("final_recommendation", {}) or {}
            
            history.append({
                "candidate_id": c_id,
                "name": c.get("name") or "Unknown Candidate",
                "email": c.get("email") or "No Email",
                "summary": c.get("summary") or "",
                "interview_id": s.get("interview_id"),
                "status": "Evaluated" if s else "Pending",
                "overall_score": scorecard_body.get("overall_score") or scorecard_body.get("overall_fit") or 0.0,
                "recommendation": rec_body.get("hiring_recommendation") or "Pending"
            })
            
        return {"history": history}
    except Exception as e:
        import logging
        logging.error("Failed to fetch history: %s", e)
        return {"history": []}
'''
    )
