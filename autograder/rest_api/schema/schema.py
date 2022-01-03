from __future__ import annotations

from typing import Optional, cast

from django.conf import settings
from django.http import HttpRequest
from rest_framework.request import Request
from rest_framework.schemas.openapi import SchemaGenerator

from .model_schema_generators import generate_model_schemas, generate_parameter_schemas
from .openapi_types import OpenAPIObject
from .utils import stderr
from .view_schema_generators import APITags


# Drf stubs doesn't have stubs for rest_framework.schemas.openapi yet.
class AGSchemaGenerator(SchemaGenerator):
    def __init__(  # type: ignore
        self,
        title=None,
        url=None,
        description=None,
        patterns=None,
        urlconf=None,
        version=None
    ):
        super().__init__(
            title='Autograder.io API',
            url=url,
            description='''
[View docs with ReDoc](/api/docs/redoc)

[View docs with Swagger](/api/docs)

### Authenticating
To obtain an API token linked to your account, visit
[https://autograder.io/web/\\_\\_apitoken\\_\\_](https://autograder.io/web/__apitoken__).
After you've logged in, you will automatically be prompted to download
a text file containing the token. If you are using a custom
deployment of autograder.io, replace "autograder.io" in the
URL with the appropriate domain.

When sending requests to the API, include the `Authorization`
header with value `Token {your token}`, where `{your token}`
should be replaced with the token string in the file you downloaded.

If your token becomes compromised, you can revoke it
by sending a DELETE request to the `/api/users/current/revoke_api_token/`
endpoint (with your token included in the "Authorization" header as before).
            ''',
            patterns=patterns,
            urlconf=urlconf,
            version=settings.VERSION,
        )

    # SchemaGenerator's return type (another TypedDict) has all optional fields.
    def get_schema(  # type: ignore
        self,
        request: Request,
        public: bool = False
    ) -> OpenAPIObject:
        stderr('Fix anyOf and oneOf examples')
        schema = cast(OpenAPIObject, super().get_schema(request=request, public=public))
        schema['components'] = {'schemas': generate_model_schemas()}
        schema['components']['parameters'] = generate_parameter_schemas()
        schema['tags'] = [{'name': item.value} for item in APITags]
        return schema
