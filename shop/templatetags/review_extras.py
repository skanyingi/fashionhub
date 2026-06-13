from django import template

register = template.Library()

@register.filter
def filter_by_user(queryset, user):
    """Checks if a specific user exists in a queryset of helpful votes"""
    if not user.is_authenticated:
        return False
    return queryset.filter(user=user).exists()
