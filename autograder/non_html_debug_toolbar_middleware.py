# Adapted from: https://gist.github.com/Benoss/9592229
# Accessed Dec. 1, 2017

from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse, StreamingHttpResponse
import json


class NonHtmlDebugToolbarMiddleware(MiddlewareMixin):

    def process_response(self, request, response):
        debug = request.GET.get('debug', 'UNSET')

        if debug != 'UNSET':
            if isinstance(response, StreamingHttpResponse):
                new_content = f'''
                    <html><body>
                        <pre>{b"".join(response.streaming_content).decode("utf-8")}</pre>
                    </body></html>'''
                response = HttpResponse(new_content)
            elif response['Content-Type'] == 'application/octet-stream':
                new_content = '<html><body>Binary Data, ' \
                    'Length: {}</body></html>'.format(len(response.content))
                response = HttpResponse(new_content)
            elif response['Content-Type'] != 'text/html':
                content = response.content.decode()
                try:
                    json_ = json.loads(content)
                    content = json.dumps(json_, sort_keys=True, indent=2)
                except ValueError:
                    pass
                response = HttpResponse('<html><body><pre>{}'
                                        '</pre></body></html>'.format(content))

        return response
