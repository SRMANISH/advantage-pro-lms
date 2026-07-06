"""Shared pagination for data-dense list endpoints.

Applied explicitly per-view (not as a global DRF default) so existing endpoints that
return a plain array keep doing so unless they opt in here.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
