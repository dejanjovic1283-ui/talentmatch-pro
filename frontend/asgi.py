from __future__ import annotations

from pathlib import Path

from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse
from starlette.routing import Route
from streamlit.web.server.starlette import App


BASE_DIR = Path(__file__).resolve().parent
SITEMAP_PATH = BASE_DIR / "static" / "sitemap.xml"


ROBOTS_TXT = """User-agent: *
Allow: /

Sitemap: https://talentmatchcv.com/sitemap.xml
"""


async def robots_txt(_request: Request) -> PlainTextResponse:
    """Serve crawler policy for the public TalentMatch Pro frontend."""
    return PlainTextResponse(
        ROBOTS_TXT,
        media_type="text/plain",
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
        },
    )


async def sitemap_xml(_request: Request) -> FileResponse:
    """Serve the canonical public sitemap from the frontend domain."""
    return FileResponse(
        SITEMAP_PATH,
        media_type="application/xml",
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
        },
    )


app = App(
    "app.py",
    routes=[
        Route(
            "/robots.txt",
            endpoint=robots_txt,
            methods=["GET"],
            name="robots_txt",
        ),
        Route(
            "/sitemap.xml",
            endpoint=sitemap_xml,
            methods=["GET"],
            name="sitemap_xml",
        ),
    ],
)
