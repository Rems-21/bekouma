from django import template

register = template.Library()


@register.filter
def daily_price(equipment, request):
    """Tarif / jour selon le compte (particulier vs entreprise). Usage : {{ eq|daily_price:request }}"""
    if not equipment:
        return 0
    user = getattr(request, 'user', None) if request else None
    return equipment.daily_price_for_user(user)
