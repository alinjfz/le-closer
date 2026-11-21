"""Promise tracker — rep promises become to-dos (F7)."""
from ..router import add_task, new_id
from ..models import Task


async def run(state, store, segment, label) -> None:
    if segment.speaker != "rep":
        return
    await add_task(state, store, Task(
        id=new_id("task"), title=segment.text[:80],
        owner="rep", origin="promise", status="queued",
    ))
    await store.log_activity(state, "PromiseTracker", f"new to-do: {segment.text[:60]}", "done")
