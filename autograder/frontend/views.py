import os
import json
import traceback
# import datetime

from django.utils import timezone

from django.views.generic.base import View
from django.views.generic.edit import CreateView, DeleteView

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.forms.forms import NON_FIELD_ERRORS

from django.shortcuts import get_object_or_404, render

from django.template import RequestContext
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth import authenticate, login, logout

from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

from autograder.frontend.frontend_utils import ExceptionLoggingView, LoginRequiredView
from autograder.models import Course, Semester, Project


class MainAppPage(ExceptionLoggingView):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return render(request, 'autograder/main_app.html', {})


from autograder.tasks import debug_task


class Tasky(ExceptionLoggingView):
    def get(self, request):
        print('request received')
        debug_task.apply_async()
        print('done queueing')
        return HttpResponse()


class LoginView(ExceptionLoggingView):
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


class LogoutView(LoginRequiredView):
    def post(self, request):
        print('logging out')
        logout(request)
        return HttpResponse()
