from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# from django.http import HttpResponse, HttpResponseForbidden
# from django.contrib.auth import authenticate, login

# from django.shortcuts import render_to_response

# from autograder.utilities.views import ExceptionLoggingView
from django.views.generic.base import View


class LoginRequiredView(View):
    @method_decorator(login_required())
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
