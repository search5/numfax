"""NamiFAX Internationalization (i18n) and Localization (l10n) module.

Following official Pyramid 2.1 Internationalization documentation:
https://docs.pylonsproject.org/projects/pyramid/en/2.1-branch/narr/i18n.html
"""

from __future__ import annotations

from typing import Any
from pyramid.i18n import TranslationStringFactory

# TranslationStringFactory for the application's unique translation domain
# Conventionally assigned to '_' for message extraction tools
_ = TranslationStringFactory("namifax")

# Supported language codes
SUPPORTED_LOCALES = ("en", "ko", "ja", "de", "fr", "es", "it", "zh")


def custom_locale_negotiator(request: Any) -> str | None:
    """Custom locale negotiator following Pyramid 2.1 specification.

    Inspects the request to determine the appropriate locale name:
    1. Explicit query parameter `_LOCALE_` or `lang`
    2. Cookie `_LOCALE_`
    3. User profile setting `current_user.language`
    4. Session attribute `session['language']`
    5. Returns None to let Pyramid fallback to `pyramid.default_locale_name` (default: 'en')
    """
    # 1. Query parameter (_LOCALE_ or lang)
    if hasattr(request, "params"):
        param_lang = request.params.get("_LOCALE_") or request.params.get("lang")
        if param_lang and param_lang in SUPPORTED_LOCALES:
            return param_lang

    # 2. Cookie (_LOCALE_)
    if hasattr(request, "cookies"):
        cookie_lang = request.cookies.get("_LOCALE_")
        if cookie_lang and cookie_lang in SUPPORTED_LOCALES:
            return cookie_lang

    # 3. Authenticated user preference
    user = getattr(request, "current_user", None)
    if user:
        user_lang = getattr(user, "language", None)
        if user_lang and user_lang in SUPPORTED_LOCALES:
            return user_lang

    # 4. Session preference
    session = getattr(request, "session", None)
    if session and hasattr(session, "get"):
        session_lang = session.get("language")
        if session_lang and session_lang in SUPPORTED_LOCALES:
            return session_lang

    # 5. Return None to let Pyramid use pyramid.default_locale_name
    return None
