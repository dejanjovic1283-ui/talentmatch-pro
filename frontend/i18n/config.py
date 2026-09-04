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
        label="English (UK)",
        native_label="English (UK)",
        flag="🇬🇧",
        html_lang="en-GB",
    ),
    "en_us": LocaleDefinition(
        code="en_us",
        label="English (US)",
        native_label="English (US)",
        flag="🇺🇸",
        html_lang="en-US",
    ),
    "sr_latn": LocaleDefinition(
        code="sr_latn",
        label="Serbian (Latin)",
        native_label="Srpski (latinica)",
        flag="🇷🇸",
        html_lang="sr-Latn",
    ),
    "de": LocaleDefinition(
        code="de",
        label="German",
        native_label="Deutsch",
        flag="🇩🇪",
        html_lang="de",
    ),
    "fr": LocaleDefinition(
        code="fr",
        label="French",
        native_label="Français",
        flag="🇫🇷",
        html_lang="fr",
    ),
    "es": LocaleDefinition(
        code="es",
        label="Spanish",
        native_label="Español",
        flag="🇪🇸",
        html_lang="es",
    ),
    "it": LocaleDefinition(
        code="it",
        label="Italian",
        native_label="Italiano",
        flag="🇮🇹",
        html_lang="it",
    ),
    "pt_br": LocaleDefinition(
        code="pt_br",
        label="Portuguese (Brazil)",
        native_label="Português (Brasil)",
        flag="🇧🇷",
        html_lang="pt-BR",
    ),
    "nl": LocaleDefinition(
        code="nl",
        label="Dutch",
        native_label="Nederlands",
        flag="🇳🇱",
        html_lang="nl",
    ),
    "ru": LocaleDefinition(
        code="ru",
        label="Russian",
        native_label="Русский",
        flag="🇷🇺",
        html_lang="ru",
    ),
    "zh_cn": LocaleDefinition(
        code="zh_cn",
        label="Chinese (Simplified)",
        native_label="简体中文",
        flag="🇨🇳",
        html_lang="zh-CN",
    ),
    "ar_ae": LocaleDefinition(
        code="ar_ae",
        label="Arabic (UAE)",
        native_label="العربية (الإمارات)",
        flag="🇦🇪",
        html_lang="ar-AE",
    ),
}

SUPPORTED_LOCALE_CODES: Final[tuple[str, ...]] = tuple(SUPPORTED_LOCALES)
