from django.http import FileResponse


# Django's FileResponse.set_headers doesn't set the Content-Length
# header if the 'name' attribute of the file-like object it's given
# is a relative path. Unfortunately, that seems to be the case with
# FieldFiles (it's name is the relative path from MEDIA_ROOT).
# See https://docs.djangoproject.com/en/2.2/_modules/django/http/response/#FileResponse
#
# This class overrides set_headers such that if Content-Length hasn't
# been set and the file-like object has a 'size' attribute,
# Content-Length is set to the value of that attribute.
class SizeFileResponse(FileResponse):
    def set_headers(self, filelike):
        super().set_headers(filelike)
        if 'Content-Length' not in self and hasattr(filelike, 'size'):
            self['Content-Length'] = filelike.size
