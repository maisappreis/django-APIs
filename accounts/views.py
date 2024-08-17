from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import views as auth_views
from rest_framework.authtoken.models import Token
from django.contrib.auth import login as auth_login
from django.http import JsonResponse


@ensure_csrf_cookie
def set_csrf_token(request):
    csrf_token = request.META.get('CSRF_COOKIE', '')
    return JsonResponse({'detail': 'CSRF cookie set successfully.', 'csrfToken': csrf_token})


class CustomLoginView(auth_views.LoginView):
    def form_invalid(self, form):
        return JsonResponse({'errors': form.errors}, status=400)

    def form_valid(self, form):
        super().form_valid(form)
        user = self.request.user
        token, created = Token.objects.get_or_create(user=user)
        self.request.session.set_test_cookie()

        return JsonResponse({
            'detail': 'Login successful',
            'token': token.key,
        })