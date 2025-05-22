from django import template

register = template.Library()

@register.filter
def any_available(sizes_with_quantities):
    return any(size_info['quantity'] > 0 for size_info in sizes_with_quantities)




@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    return dictionary.get(key)
