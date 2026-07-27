import asyncio
from app.graph.supervisor import compile_workflow

async def main():
    graph = compile_workflow()
    state = {
        "goal": "Hire a backend engineer",
        "candidates": [
            {
                "id": "c1",
                "email": "test@example.com",
                "name": "Test Candidate",
                "score": 95,
                "feedback": "Great"
            }
        ],
        "shortlist": [
            {
                "id": "c1",
                "ref_id": "c1",
                "name": "Test Candidate"
            }
        ],
        "results": {},
        "current_candidate": "c1",
        "messages": []
    }
    
    # We expect this to run up to scheduling, then stop.
    async for output in graph.astream(state):
        print(output)

if __name__ == "__main__":
    asyncio.run(main())
