from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    AuthResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserSerializer,
    tokens_for,
)


class AuthThrottleMixin:
    """Credential endpoints get a tighter, per-IP rate limit to slow down brute forcing."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


@extend_schema(tags=["Auth"])
class RegisterView(AuthThrottleMixin, generics.CreateAPIView):
    """Create an account and return a JWT pair so the client is logged in straight away."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Register a new user",
        responses={
            201: AuthResponseSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"user": UserSerializer(user).data, "tokens": tokens_for(user)},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Auth"])
class LoginView(AuthThrottleMixin, TokenObtainPairView):
    serializer_class = LoginSerializer
    authentication_classes = []

    @extend_schema(
        summary="Log in with email and password",
        responses={
            200: AuthResponseSerializer,
            401: OpenApiResponse(description="Invalid credentials"),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=["Auth"], summary="Exchange a refresh token for a new access token")
class RefreshView(AuthThrottleMixin, TokenRefreshView):
    authentication_classes = []


@extend_schema(tags=["Auth"])
class LogoutView(APIView):
    """Revoke a refresh token (it is added to the blacklist and can no longer be used)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Log out (revoke a refresh token)",
        request=LogoutSerializer,
        responses={205: OpenApiResponse(description="Token revoked"), 400: OpenApiResponse()},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
        except TokenError as exc:
            raise ValidationError({"refresh": [str(exc)]}) from exc
        if str(token.get("user_id")) != str(request.user.id):
            raise PermissionDenied("This refresh token belongs to another user.")
        token.blacklist()
        return Response(status=status.HTTP_205_RESET_CONTENT)


@extend_schema(tags=["Auth"], summary="Get the logged-in user's profile")
class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
