from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class LocaleDefinition:
    code: str
    label: str
    native_label: str
    flag: str
    html_lang: str


DEFAULT_LOCALE: Final[str] = "en"
FALLBACK_LOCALE: Final[str] = "en"
LANGUAGE_SESSION_KEY: Final[str] = "tm_locale"

SUPPORTED_LOCALES: Final[dict[str, LocaleDefinition]] = {
    "en": LocaleDefinition(
        code="en",
        label="English",
        native_label="English",
        flag="🇬🇧",
        html_lang="en",
    ),
    "sr_latn": LocaleDefinition(
        code="sr_latn",
        label="Serbian (Latin)",
        native_label="Srpski (latinica)",
        flag="🇷🇸",
        html_lang="sr-Latn",
    ),
    "sr_cyrl": LocaleDefinition(
        code="sr_cyrl",
        label="Serbian (Cyrillic)",
        native_label="Српски (ћирилица)",
        flag="🇷🇸",
        html_lang="sr-Cyrl",
    ),
    "de": LocaleDefinition(
        code="de",
        label="German",
        native_label="Deutsch",
        flag="🇩🇪",
        html_lang="de",
    ),
    "fr": LocaleDefinition(code="fr", label="French", native_label="Français", flag="🇫🇷", html_lang="fr"),
    "es": LocaleDefinition(
        code="es",
        label="Spanish",
        native_label="Español",
        flag="🇪🇸",
        html_lang="es",
    ),
    "it": LocaleDefinition(code="it", label="Italian", native_label="Italiano", flag="🇮🇹", html_lang="it"),
}

SUPPORTED_LOCALE_CODES: Final[tuple[str, ...]] = tuple(SUPPORTED_LOCALES)
