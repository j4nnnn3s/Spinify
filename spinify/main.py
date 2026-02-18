"""Entry: start API server and optional background tasks."""
import uvicorn

from spinify.api.app import app
from spinify.config import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run(
        "spinify.api.app:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
    )
