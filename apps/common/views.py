from django.db import connection
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import error_body


class HealthCheckView(APIView):
    """Liveness / readiness probe: reports whether the database is reachable."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(
        tags=["Health"],
        responses=inline_serializer(
            "HealthCheck", {"status": serializers.CharField(), "database": serializers.CharField()}
        ),
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            return Response(
                {"status": "unavailable", "database": "unreachable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok"})


def json_not_found(request, exception=None):
    return JsonResponse(
        error_body(404, "not_found", f"The URL {request.path} does not exist."), status=404
    )


def json_server_error(request):
    return JsonResponse(
        error_body(500, "server_error", "An unexpected error occurred. Please try again later."),
        status=500,
    )
