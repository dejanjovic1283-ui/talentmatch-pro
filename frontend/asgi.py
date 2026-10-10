from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse
from starlette.routing import Route
from streamlit.web.server.starlette import App

from seo_pages import PUBLIC_HTML


BASE_DIR = Path(__file__).resolve().parent
SITEMAP_PATH = BASE_DIR / "static" / "sitemap.xml"
PUBLIC_CSS_PATH = BASE_DIR / "static" / "public.css"
FAVICON_PATH = BASE_DIR / "assets" / "favicon.png"


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


async def public_css(_request: Request) -> FileResponse:
    return FileResponse(
        PUBLIC_CSS_PATH,
        media_type="text/css",
        headers={"Cache-Control": "public, max-age=3600"},
    )


async def public_favicon(_request: Request) -> FileResponse:
    return FileResponse(
        FAVICON_PATH,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


streamlit_app = App(
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
        Route("/seo/public.css", endpoint=public_css, methods=["GET"], name="public_css"),
        Route("/seo/favicon.png", endpoint=public_favicon, methods=["GET"], name="public_favicon"),
    ],
)


def _interactive_view(path: str, query_string: bytes) -> bool:
    """Preserve app links and billing callbacks, including provider parameters."""
    params = parse_qs(query_string.decode("latin-1"), keep_blank_values=True)
    if "app" in params.get("view", []):
        return True
    if path not in {"/", "/pricing"}:
        return False
    tracking_keys = {"gclid", "fbclid", "msclkid"}
    return any(
        not key.startswith("utm_") and key not in tracking_keys
        for key in params
    )


async def app(scope, receive, send):
    """Serve public HTML over HTTP; pass all app traffic to Streamlit."""
    if scope["type"] == "http" and scope.get("method") in {"GET", "HEAD"}:
        path = scope.get("path", "")
        query_string = scope.get("query_string", b"")
        if path.endswith("/") and path[:-1] in PUBLIC_HTML:
            target = path[:-1]
            if query_string:
                target += "?" + query_string.decode("latin-1")
            await RedirectResponse(target, status_code=308)(scope, receive, send)
            return
        if path in PUBLIC_HTML:
            if _interactive_view(path, query_string):
                async def send_noindex(message):
                    if message["type"] == "http.response.start":
                        message = dict(message)
                        message["headers"] = list(message.get("headers", [])) + [
                            (b"x-robots-tag", b"noindex, follow")
                        ]
                    await send(message)

                await streamlit_app(scope, receive, send_noindex)
                return
            response = HTMLResponse(
                PUBLIC_HTML[path],
                headers={
                    "Cache-Control": "public, max-age=300",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                    "Content-Security-Policy": (
                        "default-src 'none'; style-src 'self'; img-src 'self'; "
                        "font-src 'self'; base-uri 'none'; form-action 'none'; "
                        "frame-ancestors 'none'"
                    ),
                },
            )
            if scope["method"] == "HEAD":
                response.body = b""
            await response(scope, receive, send)
            return
    await streamlit_app(scope, receive, send)
