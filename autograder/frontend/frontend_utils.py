import traceback

from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


class ExceptionLoggingView(View):
    """
    View base class that catches any exceptions thrown from dispatch(),
    prints them to the console, and then rethrows.
    """
    def dispatch(self, *args, **kwargs):
        try:
            return super().dispatch(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            raise


class LoginRequiredView(ExceptionLoggingView):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
