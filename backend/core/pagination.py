"""Shared pagination for data-dense list endpoints.

Applied explicitly per-view (not as a global DRF default) so existing endpoints that
return a plain array keep doing so unless they opt in here.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def paginate_rows(request, queryset, row_fn, view=None):
    """Paginate a queryset of arbitrary objects for a hand-rolled APIView list endpoint,
    serializing each element with ``row_fn``. Returns a StandardResultsPagination envelope
    ``{count, next, previous, results}`` — the shape the FE ``unwrap``/paginator expect, so
    registers stop returning (and silently truncating) unbounded lists."""
    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(queryset, request, view=view)
    return paginator.get_paginated_response([row_fn(obj) for obj in (page or [])])
