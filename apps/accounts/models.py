from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    """Manager for a user model that logs in with email instead of a username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("A superuser must have is_staff=True and is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Application user. Identified by email; `name` replaces first/last name."""

    username = None
    first_name = None
    last_name = None

    name = models.CharField(max_length=150)
    email = models.EmailField("email address", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name
