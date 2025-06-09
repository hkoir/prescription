
from django import template
register = template.Library()
import ast
import os


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key) if dictionary else None





@register.simple_tag
def range_to(n):
    return range(1, n + 1)

@register.filter
def add_commas(value):
    try:
        return "{:,.2f}".format(float(value)) 
    except (ValueError, TypeError):
        return value 




@register.filter
def in_list(value, arg):
    if not isinstance(arg, list):
        return False
    return value in arg



@register.filter
def item_list(value, arg):
    return value in arg.split(',')




@register.filter
def in_list2(value, arg):
    if isinstance(arg, str):
        try:
            arg = ast.literal_eval(arg)  
        except (ValueError, SyntaxError):
            return False
    return value in arg




@register.filter(name='add_class')
def add_class(value, css_class):
    return value.as_widget(attrs={'class': css_class})



@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


@register.filter
def has_pending_extension_requests(task):
    return task.time_extension_requests.filter(is_approved=False).exists()



@register.filter
def dict_key(value, key):
    """Fetch value from dictionary by key."""
    return value.get(key, None)

@register.filter
def dict_get(d, key):
    return d.get(key, '')

from django import template
from django.contrib.contenttypes.models import ContentType



@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def month_names(value):
    months = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
        7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }
    return months.get(value, '')




@register.filter
def is_image(file_url):
    ext = os.path.splitext(file_url)[1].lower()
    return ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]



@register.filter
def is_pdf(file_url):
    if not file_url: 
        return False
    ext = os.path.splitext(file_url)[1].lower()
    return ext == ".pdf"



@register.filter
def status_in(queryset, status):
    return queryset.filter(status=status).count()





@register.filter(name='replace')
def replace(value, args):
    old, new = args.split(',')
    return value.replace(old, new)



@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter(name='human_readable')
def human_readable(value):
    if value:
        return value.replace('_', ' ').capitalize()  # Replace underscores and capitalize first letter
    return value