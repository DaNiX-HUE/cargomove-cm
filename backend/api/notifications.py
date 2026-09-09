"""
Notification Service
=====================
Tiny wrapper around Notification.objects.create() so every part of the
codebase that needs to notify a user does it the same way. If push/email
delivery is added later, this is the one place that needs to change.
"""

from .models import Notification


def notify(user, title, message):
    """Create (and return) a Notification for `user`."""
    return Notification.objects.create(user=user, title=title, message=message)
