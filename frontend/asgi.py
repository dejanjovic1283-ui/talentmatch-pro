from __future__ import annotations

from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from streamlit.web.server.starlette import App


ROBOTS_TXT = """User-agent: *
Allow: /

Sitemap: https://api.talentmatchcv.com/sitemap.xml
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


app = App(
    "app.py",
    routes=[
        Route(
            "/robots.txt",
            endpoint=robots_txt,
            methods=["GET"],
            name="robots_txt",
        ),
    ],
)
