"""Read-only adapter for the DataTables serverSide protocol.

Subclasses scope get_queryset() first, whitelist ORM columns and serialize rows.
Client supplied field names / search expressions are never executed as ORM paths.
"""
from functools import reduce
from operator import or_

from django.db.models import Q
from django.http import JsonResponse
from django.views import View


def nonnegative_int(value, default=0):
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    return result if 0 <= result <= 2147483647 else default


class DataTableView(View):
    http_method_names = ['get', 'head', 'options']
    order_columns = ()  # ORM fields; None for actions / other non-sortable columns.
    search_fields = ()
    default_order = ('pk',)

    def normalize_search(self, query):
        return query

    def get(self, request, *args, **kwargs):
        records = self.get_queryset()
        total = records.count()
        query = request.GET.get('search[value]', '').strip()[:500]
        if query and self.search_fields:
            query = self.normalize_search(query)
            records = records.filter(reduce(or_, (Q(**{f'{field}__icontains': query}) for field in self.search_fields)))
        filtered = records.count() if query else total
        ordering = []
        for index in range(len(self.order_columns)):
            column = request.GET.get(f'order[{index}][column]')
            if column is None:
                break
            number = nonnegative_int(column, default=-1)
            direction = request.GET.get(f'order[{index}][dir]')
            if 0 <= number < len(self.order_columns) and self.order_columns[number] and direction in ['asc', 'desc']:
                ordering.append(('-' if direction == 'desc' else '') + self.order_columns[number])
        records = records.order_by(*(ordering + ['-pk' if ordering[0].startswith('-') else 'pk'] if ordering else self.default_order))
        start = nonnegative_int(request.GET.get('start'))
        length = nonnegative_int(request.GET.get('length'), default=10)
        if length not in [10, 25, 50]:
            length = 10
        rows = [self.serialize_record(record) for record in records[start:start + length]]
        return JsonResponse({'draw': nonnegative_int(request.GET.get('draw')),
                             'recordsTotal': total, 'recordsFiltered': filtered, 'data': rows})
