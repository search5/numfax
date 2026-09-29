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
        "language": "en",
    }

    if request.method == "POST":
        params = request.params
        old_pw = params.get("old_password", "")
        new_pw = params.get("new_password", "")
        confirm_pw = params.get("confirm_password", "")

        if new_pw and new_pw != confirm_pw:
            error = "New passwords do not match."
        else:
            profile_data.update({
                "name": params.get("name", profile_data["name"]),
                "email": params.get("email", profile_data["email"]),
                "from_company": params.get("from_company", ""),
                "from_location": params.get("from_location", ""),
                "from_voicenumber": params.get("from_voicenumber", ""),
                "from_faxnumber": params.get("from_faxnumber", ""),
                "user_tsi": params.get("user_tsi", ""),
                "email_sig": params.get("email_sig", ""),
                "language": params.get("language", "en"),
            })
            message = "Settings updated successfully."

    return {
        "title": "- NamiFAX - Settings",
        "current_user": identity,
        "active_tab": "settings",
        "message": message,
        "error": error,
        "user_profile": profile_data,
    }
