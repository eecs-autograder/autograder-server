from django.apps import AppConfig


class RestApiConfig(AppConfig):
    name = 'autograder.rest_api'

    def ready(self):
        from . import signals
