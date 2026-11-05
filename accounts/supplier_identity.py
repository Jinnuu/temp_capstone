"""Portal employees are not independent procurement counterparties."""
from django.contrib.auth import get_user_model


def eligible_order_accounts(queryset=None):
    if queryset is None:
        queryset=get_user_model().objects.all()
    # Preserve legacy choices; new portal logins need their own approved canonical profile.
    return queryset.exclude(portal_membership__registered_via_portal=True, supplier_profile__isnull=True)
