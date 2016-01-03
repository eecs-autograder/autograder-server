import traceback

from django.views.generic.base import View


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
