"""OpAssure backend entrypoint.

Only a health check is exposed for now. Feature routers will be added under app/api/.
"""

from fastapi import FastAPI

app = FastAPI(title="OpAssure API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
