"""NamiFAX User Settings & Preferences View Controller."""

from __future__ import annotations

from pyramid.view import view_config


@view_config(route_name="settings", renderer="namifax:templates/settings.jinja2", permission="view")
def settings_view(request):
    """Render and handle user profile, contact details, and password settings form."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    message = None
    error = None

    profile_data = {
        "name": identity.get("name", "Administrator"),
        "email": identity.get("email", "admin@avantfax.local"),
        "from_company": "Enterprise Inc.",
        "from_location": "Headquarters",
        "from_voicenumber": "+1-555-0100",
        "from_faxnumber": "+1-555-0199",
        "user_tsi": "ENTERPRISE-HQ",
        "email_sig": "-- \nBest regards,\nNamiFAX Administrator",
    }

    # Determine current language from cookie, session, or identity
    current_lang = "en"
    if hasattr(request, "cookies") and request.cookies.get("_LOCALE_"):
        current_lang = request.cookies.get("_LOCALE_")
    elif hasattr(request, "session") and request.session.get("language"):
        current_lang = request.session.get("language")
    elif identity.get("language"):
        current_lang = identity.get("language")

    profile_data["language"] = current_lang

    if request.method == "POST":
        params = request.params
        old_pw = params.get("old_password", "")
        new_pw = params.get("new_password", "")
        confirm_pw = params.get("confirm_password", "")

        if new_pw and new_pw != confirm_pw:
            error = "New passwords do not match."
        else:
            selected_lang = params.get("language", "en")
            profile_data.update({
                "name": params.get("name", profile_data["name"]),
                "email": params.get("email", profile_data["email"]),
                "from_company": params.get("from_company", ""),
                "from_location": params.get("from_location", ""),
                "from_voicenumber": params.get("from_voicenumber", ""),
                "from_faxnumber": params.get("from_faxnumber", ""),
                "user_tsi": params.get("user_tsi", ""),
                "email_sig": params.get("email_sig", ""),
                "language": selected_lang,
            })

            # Update session language
            if hasattr(request, "session"):
                request.session["language"] = selected_lang

            # Set _LOCALE_ cookie for immediate persistence across requests
            if hasattr(request, "response"):
                request.response.set_cookie("_LOCALE_", selected_lang, max_age=31536000, path="/")

            message = "Settings updated successfully."

    return {
        "title": "- NamiFAX - Settings",
        "current_user": identity,
        "active_tab": "settings",
        "message": message,
        "error": error,
        "user_profile": profile_data,
    }
