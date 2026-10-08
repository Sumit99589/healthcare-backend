from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import User


class UserCreationAdminForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("email", "name")


class UserChangeAdminForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
