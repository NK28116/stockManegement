from fastapi import APIRouter

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.post("/execute")
async def execute_action(action_type: str):
    return {
        "status": "success",
        "action": action_type,
        "message": "Action executed successfully (mock)",
    }


@router.get("/status")
async def get_status():
    """
    Returns the current status of actions (mocked for now).
    """
    return {
        "can_update": True,
        "cooldown_remaining_minutes": 0,
        "is_updating": False,
        "is_analyzing": False,
    }
