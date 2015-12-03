# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.fields
import django.core.validators
import re


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0034_studenttestsuitebase_compiler_flags'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuitebase',
            name='compiler_flags',
            field=autograder.models.fields.StringListField(blank=True, default=list, base_field=models.CharField(blank=True, max_length=255), size=None, validators=[django.core.validators.RegexValidator(re.compile('[a-zA-Z0-9-_=.]+', 32))]),
        ),
    ]
