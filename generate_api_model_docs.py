# #! /usr/bin/env python3
#
# from collections import OrderedDict
# import inspect
# import json
# import sys
# from typing import Type, Sequence
#
# from django.core.management.base import BaseCommand
# from django.db import models
# import autograder.core.models as ag_models
#
#
# class Command(BaseCommand):
#     help = 'FIXME'
#
#     # def add_arguments(self, parser):
#     #     parser.add_argument('course_name')
#     #     parser.add_argument('project_name')
#     #     parser.add_argument('target_course_name')
#
#     def handle(self, *args, **kwargs):
#         ag_model_classes = inspect.getmembers(ag_models, is_ag_model)
#
#         results = [str(APIModelInfo(class_name, ag_model_class))
#                    for class_name, ag_model_class in ag_model_classes]
#
#         # json.dump(results, sys.stdout, indent=4)
#
#
# def is_ag_model(member):
#     return (inspect.isclass(member) and
#             issubclass(member, ag_models.AutograderModel) and
#             member is not ag_models.AutograderModel)
#
#
# class APIModelInfo:
#     def __init__(self, ag_model_class):
#         self.ag_model_class = ag_model_class
#         self.fields = []
#         for field_name in self.ag_model_class.get_serializable_fields():
#             read_only = field_name not in self.ag_model_class.get_editable_fields()
#             if
#
#             # if it's read-only, mark as read only
#             # if it's a property, grab it's docstring
#             # if it's a field, grab it's help text
#             # if it's a property, grab type from typeinfo
#             # if it's a field, deduce type from relationship and/or field type
#             # if it's a ManyToOne, it's a reverse foreign key, handle appropriately
#
#     def __str__(self):
#         return json.dumps(self.fields, indent=4)
#
#
# class APIModelFieldInfo:
#     def __init__(self, name: str, type_: str, docstring: str, read_only: bool):
#         self.name = name
#         self.type = type_
#         self.docstring = docstring
#         self.read_only = read_only
#
#     def __str__(self):
#         return '''    "{name}": {{
#         "type": "{type}",
#         "docs": "{docs}",
#         "read_only": "{read_only}"
#     }}
# '''.format(self.name, self.type, self.docstring, self.read_only)
