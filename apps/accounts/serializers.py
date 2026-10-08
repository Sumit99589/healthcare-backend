from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "date_joined"]
        read_only_fields = fields


class TokenPairSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    """Shape of the register / login responses (used for API docs)."""

    user = UserSerializer()
    tokens = TokenPairSerializer()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ["name", "email", "password"]
        extra_kwargs = {
            # Uniqueness is checked case-insensitively in validate_email instead.
            "email": {"validators": []},
        }

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        # Run Django's password validators with the would-be user so that
        # "password too similar to your email/name" is caught as well.
        candidate = User(name=attrs.get("name", ""), email=attrs.get("email", ""))
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    """Email + password -> JWT pair, plus the user's profile."""

    default_error_messages = {
        "no_active_account": "Invalid email or password.",
    }

    def validate(self, attrs):
        attrs[self.username_field] = attrs[self.username_field].strip().lower()
        tokens = super().validate(attrs)
        return {
            "user": UserSerializer(self.user).data,
            "tokens": {"refresh": tokens["refresh"], "access": tokens["access"]},
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="The refresh token to revoke.")
