from dotenv import load_dotenv
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_health import health
from middleware import CustomGZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from Secweb.XContentTypeOptions import XContentTypeOptions
from Secweb.XFrameOptions import XFrame

from router import router

load_dotenv(override=True)
logger = logging.getLogger(__name__)
CHUNK_DIR = os.path.join(os.path.dirname(__file__), "chunks")
MERGED_DIR = os.path.join(os.path.dirname(__file__), "merged_files")



def healthy_condition() -> dict:
    """Return a healthy status for health check."""
    return {"healthy": True}

def healthy() -> bool:
    """Return True for health check."""
    return True


def create_app():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    app = FastAPI(title="Graph Builder(Neo4j)", version="0.0.1")
    app.add_middleware(XContentTypeOptions)
    app.add_middleware(
        CustomGZipMiddleware,
        minimum_size=1000,
        compresslevel=5,
        paths=[
            "/sources_list", "/url/scan", "/extract", "/chat_bot", "/chunk_entities", "/get_neighbours", "/graph_query",
            "/schema", "/populate_graph_schema", "/get_unconnected_nodes_list", "/get_duplicate_nodes", "/fetch_chunktext",
            "/schema_visualization"
        ]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))
    app.add_api_route("/health", health([healthy_condition, healthy]))
    app.include_router(router)

    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=7860)





