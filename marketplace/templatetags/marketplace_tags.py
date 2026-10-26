from django import template

register = template.Library()


@register.filter
def rupiah(value):
    try:
        return f"Rp{int(value):,}".replace(',', '.')
    except (TypeError, ValueError):
        return value


@register.simple_tag
def stars(rating):
    rating = max(0, min(int(rating or 0), 5))
    return '\u2605' * rating + '\u2606' * (5 - rating)
