"""Unit tests for NamiFAX Babel/gettext i18n localization system.

Following Pyramid 2.1 i18n testing documentation.
"""

from pyramid import testing
from pyramid.i18n import TranslationStringFactory, get_localizer

from namifax.i18n import _, custom_locale_negotiator, SUPPORTED_LOCALES


class DummyUser:
    def __init__(self, language: str = "en"):
        self.language = language


class DummyRequest:
    def __init__(self, params=None, cookies=None, current_user=None, session=None):
        self.params = params or {}
        self.cookies = cookies or {}
        self.current_user = current_user
        self.session = session or {}


def test_supported_locales():
    assert "en" in SUPPORTED_LOCALES
    assert "ko" in SUPPORTED_LOCALES


def test_locale_negotiator_priority():
    # 1. Query parameter takes highest precedence
    req1 = DummyRequest(
        params={"_LOCALE_": "ko"},
        cookies={"_LOCALE_": "en"},
        current_user=DummyUser("en"),
    )
    assert custom_locale_negotiator(req1) == "ko"

    # 2. Cookie takes precedence over user/session
    req2 = DummyRequest(
        cookies={"_LOCALE_": "ko"},
        current_user=DummyUser("en"),
    )
    assert custom_locale_negotiator(req2) == "ko"

    # 3. User profile language takes precedence over fallback
    req3 = DummyRequest(current_user=DummyUser("ko"))
    assert custom_locale_negotiator(req3) == "ko"

    # 4. Fallback returns None for default_locale_name ('en')
    req4 = DummyRequest()
    assert custom_locale_negotiator(req4) is None


def test_translation_korean_and_english():
    config = testing.setUp(settings={
        "pyramid.default_locale_name": "en",
        "jinja2.i18n.domain": "namifax",
    })
    try:
        config.add_translation_dirs("namifax:locale")
        config.set_locale_negotiator(custom_locale_negotiator)

        # Korean request
        req_ko = testing.DummyRequest(params={"_LOCALE_": "ko"})
        localizer_ko = get_localizer(req_ko)
        assert localizer_ko.translate(_("Inbox")) == "받은 팩스함"
        assert localizer_ko.translate(_("Send Fax")) == "팩스 보내기"
        assert localizer_ko.translate(_("Archive")) == "보관함"

        # English request (default)
        req_en = testing.DummyRequest()
        localizer_en = get_localizer(req_en)
        assert localizer_en.translate(_("Inbox")) == "Inbox"
        assert localizer_en.translate(_("Send Fax")) == "Send Fax"
        assert localizer_en.translate(_("Archive")) == "Archive"

    finally:
        testing.tearDown()
