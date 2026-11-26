"""Static URLs that change when a locally served asset changes."""

from hashlib import sha256
from pathlib import Path

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def versioned_static(path):
    url = static(path)
    source = finders.find(path)
    if source:
        digest = sha256(Path(source).read_bytes()).hexdigest()[:12]
        return f'{url}?v={digest}'
    return url
