from __future__ import annotations

import uvicorn
from api import create_app

app = create_app()


@app.on_event("startup")
async def _increase_thread_pool():
    import anyio
    anyio.to_thread.current_default_thread_limiter().total_tokens = 5000


if __name__ == "__main__":
    uvicorn.run(app, access_log=False, log_level="info")
