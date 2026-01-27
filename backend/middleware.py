from typing import List
from starlette.types import ASGIApp, Receive, Scope, Send
from fastapi.middleware.gzip import GZipMiddleware



class CustomGZipMiddleware:
    """Custom GZip middleware to compress responses for specific paths."""

    def __init__(self, app: ASGIApp, paths: List[str], minimum_size: int = 1000, compresslevel: int = 5):
        self.app = app
        self.paths = paths
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        should_compress = any(path.startswith(gzip_path) for gzip_path in self.paths)
        if not should_compress:
            return await self.app(scope, receive, send)
        gzip_middleware = GZipMiddleware(
            app=self.app,
            minimum_size=self.minimum_size,
            compresslevel=self.compresslevel
        )
        await gzip_middleware(scope, receive, send)