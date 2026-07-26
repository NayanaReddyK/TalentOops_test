"""Dev-only demo seed: populates the in-memory store so dashboards render offline."""
from app.config import settings
from app.services.database import db


async def seed_demo() -> None:
    if settings.is_production or not settings.is_offline_mode:
        return
    if await db.query("roles"):  # idempotent
        return
    role = await db.insert("roles", {
        "id": "r1", "jd": "Senior Backend Engineer", "frozen": True,
        "difficulty_level": "L2",
        "rubric": {"difficulty_level": "L2", "competencies": [
            {"competency_id": "python", "keywords": ["pytorch", "asyncio"]},
            {"competency_id": "sql", "keywords": ["postgres", "index"]},
        ]}})
    cand = await db.insert("candidates", {
        "id": "c1", "role_id": role["id"], "name": "Alex",
        "resume": "PyTorch, asyncio, postgres, kafka"})
    # cohorts for the Fairness Lens: A visible (n=6), B suppressed (n=2), C drifted (n=5)
    for cohort, count, diff in (("A", 6, 1.0), ("B", 2, 3.0), ("C", 5, 3.0)):
        for i in range(count):
            cid = f"{cohort.lower()}{i}"
            await db.insert("demographics", {"candidate_id": cid,
                                             "cohort": {"gender": cohort}})
            await db.insert("interviews", {
                "role_id": role["id"], "candidate_id": cid,
                "questions": [{"difficulty_estimate": diff}]})
    await db.insert("scorecards", {"candidate_id": cand["id"], "scorecard": {
        "competencies": [], "overall_fit": 1.0, "needs_human_review": False}})
