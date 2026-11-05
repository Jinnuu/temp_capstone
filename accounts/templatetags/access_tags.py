from django import template
from accounts.rbac import can, required_capability
register = template.Library()


@register.filter
def can_access(name, user):
    cap = required_capability(name)
    return bool(cap and can(user, cap))
