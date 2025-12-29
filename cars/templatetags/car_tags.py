from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def format_naira(value):
    """
    Format price in Nigerian Naira with proper formatting
    Usage: {{ car.price|format_naira }}
    Output: ₦5,000,000
    """
    try:
        value = float(value)
        return f"₦{value:,.0f}"
    except (ValueError, TypeError):
        return value


@register.filter
def format_mileage(value):
    """
    Format mileage with comma separator
    Usage: {{ car.mileage|format_mileage }}
    Output: 45,000 km
    """
    try:
        if value:
            return f"{int(value):,} km"
        return "N/A"
    except (ValueError, TypeError):
        return "N/A"


@register.filter
def condition_badge_class(condition):
    """
    Return CSS class for condition badge
    Usage: <span class="{{ car.condition|condition_badge_class }}">
    """
    badge_classes = {
        'new': 'bg-green-100 text-green-800',
        'foreign_used': 'bg-cyan-100 text-cyan-800',
        'local_used': 'bg-orange-100 text-orange-800',
    }
    return badge_classes.get(condition, 'bg-gray-100 text-gray-800')


@register.filter
def condition_display(condition):
    """
    Return human-readable condition text
    """
    displays = {
        'new': 'Brand New',
        'foreign_used': 'Foreign Used (Tokunbo)',
        'local_used': 'Locally Used',
    }
    return displays.get(condition, condition)


@register.simple_tag
def get_car_specs(car):
    """
    Return a list of key specs for quick display
    Usage: {% get_car_specs car as specs %}
    """
    specs = []
    
    if car.year:
        specs.append(f"{car.year}")
    
    if car.transmission:
        specs.append(car.get_transmission_display())
    
    if car.fuel_type:
        specs.append(car.get_fuel_type_display())
    
    if car.mileage:
        specs.append(f"{car.mileage:,} km")
    
    return specs


@register.inclusion_tag('cars/partials/car_card.html')
def render_car_card(car, show_condition=True):
    """
    Render a car card component
    Usage: {% render_car_card car %}
    """
    return {
        'car': car,
        'show_condition': show_condition,
    }


@register.filter
def truncate_words_custom(value, arg):
    """
    Truncate text to specified number of words
    Usage: {{ car.description|truncate_words_custom:20 }}
    """
    try:
        words = value.split()
        if len(words) > int(arg):
            return ' '.join(words[:int(arg)]) + '...'
        return value
    except (ValueError, AttributeError):
        return value


@register.simple_tag
def get_filter_query_string(request, **kwargs):
    """
    Build query string for filters while preserving existing params
    Usage: {% get_filter_query_string request page=2 %}
    """
    query_dict = request.GET.copy()
    for key, value in kwargs.items():
        if value:
            query_dict[key] = value
        elif key in query_dict:
            del query_dict[key]
    
    return query_dict.urlencode()


@register.filter
def get_range(value):
    """
    Return range for pagination
    Usage: {% for i in page_obj.paginator.num_pages|get_range %}
    """
    try:
        return range(1, int(value) + 1)
    except (ValueError, TypeError):
        return range(0)