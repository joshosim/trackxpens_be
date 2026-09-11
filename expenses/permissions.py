from rest_framework.permissions import BasePermission


class HasPin(BasePermission):
    message = "Set a PIN before accessing the app."

    def has_permission(self, request, view):
        return bool(getattr(request.user, "profile", None) and request.user.profile.pin_hash)
