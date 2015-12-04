# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.fields
import re
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuitebase',
            name='compiler_flags',
            field=autograder.models.fields.StringListField(size=None, default=list, allow_empty_strings=False, strip_strings=True, blank=True, string_validators=[django.core.validators.RegexValidator(re.compile('^[a-zA-Z0-9-_=.]+$', 32))]),
        ),
    ]
