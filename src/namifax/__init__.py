"""NamiFAX Modern Enterprise Fax Platform Package with Pyramid, SQLAlchemy, and Security Policy."""

from __future__ import annotations

import os

__version__ = "4.0.0"


def create_app(global_config=None, **settings):
    """Pyramid application factory configuring SQLAlchemy, SecurityPolicy, routes, and views."""
    from pyramid.config import Configurator
    import namifax
    from namifax.security import NamiFaxSecurityPolicy, RootContext

    tpl_dir = os.path.join(os.path.dirname(__file__), "templates")
    settings.setdefault("jinja2.directories", tpl_dir)
    settings.setdefault("pyramid.default_locale_name", "en")
    settings.setdefault("jinja2.i18n.domain", "namifax")

    from namifax.i18n import custom_locale_negotiator

    with Configurator(package=namifax, settings=settings, root_factory=RootContext) as config:
        # Set modern Pyramid Security Policy
        policy = NamiFaxSecurityPolicy()
        config.set_security_policy(policy)
        config.registry.namifax_policy = policy

        # Short-lived signed cookie for flow state (the 2FA step, passkey challenges). Login itself is the
        # token cookie of the security policy, not this one.
        config.set_session_factory(_session_factory(settings))

        from namifax.common.secretbox import set_default_key
        set_default_key(settings.get("secret.key"))

        # Include i18n translation directories & negotiator
        config.add_translation_dirs("namifax:locale")
        config.set_locale_negotiator(custom_locale_negotiator)

        # Include Jinja2 and SQLAlchemy models (creates the single engine, spec 48)
        config.include("pyramid_jinja2")
        config.include(".models")

        # Initialize DB tables and seed data on the injected engine
        from namifax.db.bootstrap import ensure_schema
        ensure_schema(config.registry["dbengine"], settings)

        config.include(".routes")
        config.add_tween("namifax.origin_guard.origin_guard_factory")

        # Scan views for @view_config decorators
        config.scan(".views")

        return config.make_wsgi_app()


def _session_factory(settings):
    """Signed-cookie session; the secret comes from ``session.secret`` or ``NAMIFAX_SESSION_SECRET``.

    Without one a random secret is used, which is fine for a single process but means that a restart, or a
    request answered by another worker, loses the flow state. Production should set a fixed secret.
    """
    import logging
    import secrets

    from pyramid.session import SignedCookieSessionFactory

    secret = settings.get("session.secret") or os.environ.get("NAMIFAX_SESSION_SECRET")
    if not secret:
        secret = secrets.token_hex(32)
        logging.getLogger("namifax").warning(
            "No session.secret / NAMIFAX_SESSION_SECRET configured: using a random one for this process only")
    return SignedCookieSessionFactory(
        secret,
        cookie_name="namifax_flow",
        httponly=True,
        samesite="Lax",
        secure=str(settings.get("session.secure", "false")).lower() in ("1", "true", "yes"),
        timeout=1800,
    )


main = create_app

