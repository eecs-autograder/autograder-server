from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.http import HttpRequest
from rest_framework.schemas.openapi import SchemaGenerator  # type: ignore

from autograder.rest_api.schema.model_schema_generators import (generate_model_schemas,
                                                                generate_parameter_schemas)
from autograder.rest_api.schema.openapi_types import OpenAPIObject
from autograder.rest_api.schema.utils import stderr
from autograder.rest_api.schema.view_schema_generators import APITags


# Drf stubs doesn't have stubs for rest_framework.schemas.openapi yet.
class AGSchemaGenerator(SchemaGenerator):  # type: ignore
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
            description=description,
            patterns=patterns,
            urlconf=urlconf,
            version=settings.VERSION,
        )

    def get_schema(
        self,
        request: Optional[HttpRequest] = None,
        public: bool = False
    ) -> OpenAPIObject:
        stderr('Fix anyOf and oneOf examples')
        schema: OpenAPIObject = super().get_schema(request=request, public=public)
        schema['components'] = {'schemas': generate_model_schemas()}
        schema['components']['parameters'] = generate_parameter_schemas()
        schema['tags'] = [{'name': item.value} for item in APITags]
        return schema
