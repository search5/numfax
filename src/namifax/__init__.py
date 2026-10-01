"""NamiFAX Modern Enterprise Fax Platform Package with Pyramid, SQLAlchemy, and Security Policy."""

from __future__ import annotations

import os

__version__ = "4.0.0"


def create_app(global_config=None, **settings):
    """Pyramid application factory configuring SQLAlchemy, SecurityPolicy, routes, and views."""
    try:
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

            # Include i18n translation directories & negotiator
            config.add_translation_dirs("namifax:locale")
            config.set_locale_negotiator(custom_locale_negotiator)

            # Include Jinja2 and SQLAlchemy models (creates the single engine, spec 48)
            config.include("pyramid_jinja2")
            config.include(".models")

            # Initialize DB tables and seed data on the injected engine
            from namifax.db.provider import open_db
            from namifax.db.schema import init_database_tables
            boot_db = open_db(config.registry["dbengine"])
            try:
                init_database_tables(boot_db)
            finally:
                boot_db.disconnect()

            config.include(".routes")

            # Scan views for @view_config decorators
            config.scan(".views")

            return config.make_wsgi_app()

    except ImportError:
        from namifax.web.app import create_app as fallback_create_app
        return fallback_create_app()


main = create_app

