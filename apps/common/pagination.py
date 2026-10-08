from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """`?page=<n>&page_size=<n>` pagination, capped at 100 items per page."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
