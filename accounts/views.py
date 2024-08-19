from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import views as auth_views
from rest_framework.authtoken.models import Token
from django.http import JsonResponse
# from django.contrib.auth import logout
# from django.views.generic import View
# from django.views.decorators.csrf import csrf_exempt


@ensure_csrf_cookie
def set_csrf_token(request):
    csrf_token = request.META.get('CSRF_COOKIE', '')
    print('set_csrf_token', csrf_token)
    return JsonResponse({'detail': 'CSRF cookie set successfully.', 'csrfToken': csrf_token})


@ensure_csrf_cookie
def get_csrf_token(request):
    print('get_csrf_token', JsonResponse({'csrfToken': request.META.get('CSRF_COOKIE')}))
    return JsonResponse({'csrfToken': request.META.get('CSRF_COOKIE')})


class CustomLoginView(auth_views.LoginView):
    def form_invalid(self, form):
        return JsonResponse({'errors': form.errors}, status=400)

    def form_valid(self, form):
        super().form_valid(form)
        user = self.request.user
        print('user', user)

        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        print('token', token)
        print('token.key', token.key)

        self.request.session.set_test_cookie()

        return JsonResponse({
            'detail': 'Login successful',
            'token': token.key,
        })


# class CustomLogoutView(View):
#     @csrf_exempt
#     def post(self, request, *args, **kwargs):
#         Token.objects.filter(user=request.user).delete()
#         logout(request)
#         return JsonResponse({'message': 'Logout realizado com sucesso.'}, status=200)