from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsCreatorOrReadOnly(BasePermission):
    """
    Any authenticated user may read the object; only the user who created it (or a
    staff member) may modify or delete it.
    """

    message = "Only the user who created this record can modify or delete it."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_staff or obj.created_by_id == request.user.id
