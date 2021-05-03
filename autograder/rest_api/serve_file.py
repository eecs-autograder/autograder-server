from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse


def serve_file(path: Path, content_type: str = 'application/octet-stream') -> HttpResponse:
    """
    Returns a response that serves the file specified by "path".
    "path" must be an absolute path that starts with settings.MEDIA_ROOT.

    If the setting USE_NGINX_X_ACCEL is True, the response will be a
    plain HttpResponse with the X-Accel-Redirect header set.
    If USE_NGINX_X_ACCEL is False, this function will return a FileResponse.
    Note that USE_NGINX_X_ACCEL defaults to True in production mode
    (when DEBUG is True) and defaults to False in development mode
    (when DEBUG is False. This allows us to run our existing unit tests
    unchanged (since the unit tests don't use a live server or nginx).
    """

    if settings.USE_NGINX_X_ACCEL:
        assert path.is_absolute()
        response = HttpResponse()
        response['Content-Type'] = content_type
        response['Content-Disposition'] = f'attachment; filename={path.name}'
        response['X-Accel-Redirect'] = '/protected/' + str(path.relative_to(settings.MEDIA_ROOT))
        return response
    else:
        return FileResponse(open(path, 'rb'), content_type=content_type)
