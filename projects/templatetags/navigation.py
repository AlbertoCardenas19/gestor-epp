from django import template
from django.urls import reverse

register = template.Library()

GROUPS = (
    ('General', (('projects:home', 'Inicio', 'Inicio', 'home'),)),
    ('Proyectos', (('projects:list', 'Proyectos', 'Proyectos', 'projects'),)),
    ('Inventario', (
        ('stock:list', 'Inventario general', 'Stock', 'stock'),
        ('catalog:list', 'Catálogo de elementos', 'Catálogo', 'catalog'),
        ('catalog:categories', 'Categorías', 'Categorías', 'catalog'),
    )),
    ('Compras', (
        ('purchases:list', 'Facturas', 'Facturas', 'purchases'),
        ('purchases:suppliers', 'Proveedores', 'Proveedor', 'projects'),
    )),
)


def current_section(match):
    if match.view_name == 'projects:home':
        return 'projects:home'
    if match.namespace in ('projects', 'inventory', 'requests'):
        return 'projects:list'
    if match.namespace == 'catalog' and (
        match.url_name == 'categories' or match.url_name.startswith('category-')
    ):
        return 'catalog:categories'
    if match.namespace == 'catalog' or match.view_name == 'stock:item':
        return 'catalog:list'
    if match.namespace == 'stock':
        return 'stock:list'
    if match.namespace == 'purchases':
        if match.url_name == 'suppliers' or match.url_name.startswith(('supplier', 'price-')):
            return 'purchases:suppliers'
        return 'purchases:list'
    return None


@register.simple_tag
def sidebar_navigation(match):
    current = current_section(match) if match else None
    groups = []
    active = None
    for title, definitions in GROUPS:
        links = []
        for route, label, short_label, icon in definitions:
            link = {'label': label, 'short_label': short_label, 'icon': icon, 'url': reverse(route)}
            if route == current:
                link['current'] = 'page' if route == match.view_name else 'location'
                active = link
            links.append(link)
        groups.append({'title': title, 'links': links})
    return {'groups': groups, 'active': active}
