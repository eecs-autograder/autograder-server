# from autograder.security.views import LoginRequiredView

from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.shortcuts import render

from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth import authenticate, login

from django.shortcuts import render_to_response

from autograder.utilities.views import ExceptionLoggingView


class MainAppPage(ExceptionLoggingView):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return render(request, 'web_interface/main_app.html', {})


class LoginView(ExceptionLoggingView):
    def get(self, request):
        print(request)
        redirect_reason = request.GET.get('reason', '')
        return render_to_response(
            'web_interface/login.html', {'redirect_reason': redirect_reason})

    # def get(self, request):
    #     redirect_url = request.GET.get('next', reverse('main-app-page'))
    #     if request.user.is_authenticated():
    #         return HttpResponseRedirect(redirect_url)

    #     return render(request, 'autograder/login.html',
    #                   {'redirect_url': redirect_url})

    def post(self, request):
        user = authenticate(token=request.POST['idtoken'])
        if user is None:
            return HttpResponseForbidden('Authentication failure')

        login(request, user)
        return HttpResponse()
