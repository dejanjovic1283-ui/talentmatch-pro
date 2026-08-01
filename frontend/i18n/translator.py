from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st

from .config import (
    DEFAULT_LOCALE,
    FALLBACK_LOCALE,
    LANGUAGE_SESSION_KEY,
    SUPPORTED_LOCALES,
)
from .locales import CATALOGS


def _normalize_locale(locale: str | None) -> str:
    candidate = str(locale or "").strip().lower()
    return candidate if candidate in SUPPORTED_LOCALES else DEFAULT_LOCALE


def init_i18n(default_locale: str = DEFAULT_LOCALE) -> str:
    """Initialize and return the current locale."""
    normalized_default = _normalize_locale(default_locale)
    current = _normalize_locale(st.session_state.get(LANGUAGE_SESSION_KEY, normalized_default))
    st.session_state[LANGUAGE_SESSION_KEY] = current
    return current


def get_locale() -> str:
    return init_i18n()


def set_locale(locale: str) -> str:
    normalized = _normalize_locale(locale)
    st.session_state[LANGUAGE_SESSION_KEY] = normalized
    return normalized


def get_html_lang(locale: str | None = None) -> str:
    code = _normalize_locale(locale or get_locale())
    return SUPPORTED_LOCALES[code].html_lang


def _lookup(catalog: Mapping[str, Any], dotted_key: str) -> Any:
    value: Any = catalog
    for segment in dotted_key.split("."):
        if not isinstance(value, Mapping) or segment not in value:
            return None
        value = value[segment]
    return value


def t(
    key: str,
    *,
    locale: str | None = None,
    default: str | None = None,
    **variables: Any,
) -> str:
    """
    Translate a dotted key with English fallback.

    Unknown keys return `default` when provided, otherwise the key itself.
    """
    selected = _normalize_locale(locale or get_locale())
    value = _lookup(CATALOGS[selected], key)

    if value is None and selected != FALLBACK_LOCALE:
        value = _lookup(CATALOGS[FALLBACK_LOCALE], key)

    if value is None:
        value = default if default is not None else key

    rendered = str(value)
    if variables:
        try:
            rendered = rendered.format(**variables)
        except (KeyError, ValueError):
            pass
    return rendered


def get_seo(locale: str | None = None) -> dict[str, str]:
    selected = _normalize_locale(locale or get_locale())
    return {
        "title": t("seo.title", locale=selected),
        "description": t("seo.description", locale=selected),
        "keywords": t("seo.keywords", locale=selected),
        "html_lang": get_html_lang(selected),
    }
