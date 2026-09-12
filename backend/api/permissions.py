"""
Role-based permissions.

Without these, e.g. a driver POSTing to /shipments/ would hit
Customer.objects.get(user=request.user) in the view and blow up with an
unhandled DoesNotExist (500 error) instead of a clean 403. Attach these
to the actions that are role-specific.
"""

from rest_framework.permissions import BasePermission


class IsCustomer(BasePermission):
    message = 'Only customer accounts can perform this action.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == 'SENDER')


class IsDriver(BasePermission):
    message = 'Only driver accounts can perform this action.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == 'DRIVER')
