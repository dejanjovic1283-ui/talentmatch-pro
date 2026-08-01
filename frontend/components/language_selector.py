from __future__ import annotations

import streamlit as st

from i18n import SUPPORTED_LOCALES, get_locale, set_locale, t


def render_language_selector(*, compact: bool = False, key: str = "tm_language_selector") -> str:
    """Render the global language selector and return the active locale code."""
    current = get_locale()
    locale_codes = list(SUPPORTED_LOCALES)

    def format_locale(code: str) -> str:
        item = SUPPORTED_LOCALES[code]
        return f"{item.flag} {item.native_label}"

    selected = st.selectbox(
        t("language.title"),
        options=locale_codes,
        index=locale_codes.index(current),
        format_func=format_locale,
        help=None if compact else t("language.help"),
        key=key,
        label_visibility="collapsed" if compact else "visible",
    )

    if selected != current:
        set_locale(selected)
        st.rerun()

    return selected
