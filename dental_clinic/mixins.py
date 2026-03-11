class UserQuerySetMixin:
    """
    Ensures queryset is always filtered by authenticated user.
    """

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class UserCreateMixin:
    """
    Automatically attaches the authenticated user on object creation.
    """

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)