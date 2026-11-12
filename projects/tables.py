from functools import reduce
from operator import or_

from django.db.models import Q


class TableViewMixin:
    """Búsqueda, ordenación permitida y paginación sin cargar todas las filas."""
    paginate_by = 10
    search_fields = ()
    sort_options = ()
    default_sort = ''
    table_columns = ()

    def table_query(self):
        return self.request.GET.get('q', '').strip()

    def table_sort(self):
        value = self.request.GET.get('sort', self.default_sort)
        return value if value in {key for key, _, _ in self.sort_options} else self.default_sort

    def get_paginate_by(self, queryset):
        value = self.request.GET.get('per_page', '10')
        return int(value) if value in ['10', '25', '50'] else 10

    def filter_table(self, queryset):
        query = self.table_query()
        if query:
            queryset = queryset.filter(reduce(or_, (Q(**{f'{field}__icontains': query}) for field in self.search_fields)))
        ordering = next(fields for key, _, fields in self.sort_options if key == self.table_sort())
        return queryset.order_by(*ordering)

    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(queryset, page_size)
        page = paginator.get_page(self.request.GET.get('page', 1))
        return paginator, page, page.object_list, page.has_other_pages()

    def get_context_data(self, **kwargs):
        current_sort = self.table_sort()
        columns = []
        for label, ascending, descending in self.table_columns:
            direction = 'ascending' if current_sort == ascending else 'descending' if current_sort == descending else 'none'
            columns.append({'label': label, 'direction': direction,
                            'next_sort': descending if current_sort == ascending else ascending})
        return super().get_context_data(
            columns=columns, q=self.table_query(), sort=self.table_sort(), per_page=self.get_paginate_by(None),
            sort_options=[(key, label) for key, label, _ in self.sort_options], **kwargs,
        )
