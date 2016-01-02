import traceback

from django.views.generic import View
from django.core import exceptions
from django import http


class EndpointBase(View):
    def dispatch(self, *args, **kwargs):
        try:
            return super().dispatch(*args, **kwargs)
        except exceptions.ObjectDoesNotExist as e:
            # print(e)
            return http.HttpResponseNotFound()
        except exceptions.PermissionDenied as e:
            # print(e)
            return http.HttpResponseForbidden()
        except exceptions.ValidationError as e:
            # print(e)
            try:
                return http.JsonResponse(
                    e.message_dict, status=400)
            except AttributeError:
                return http.HttpResponseBadRequest(e)
        except Exception:
            traceback.print_exc()
            raise
