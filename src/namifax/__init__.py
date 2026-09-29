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

        with Configurator(package=namifax, settings=settings, root_factory=RootContext) as config:
            # Set modern Pyramid Security Policy
            policy = NamiFaxSecurityPolicy()
            config.set_security_policy(policy)
            config.registry.namifax_policy = policy

            # Include Jinja2 and SQLAlchemy models
            config.include("pyramid_jinja2")
            config.include(".models")
            config.include(".routes")

            # Scan views for @view_config decorators
            config.scan(".views")

            return config.make_wsgi_app()

    except ImportError:
        from namifax.web.app import create_app as fallback_create_app
        return fallback_create_app()


main = create_app

