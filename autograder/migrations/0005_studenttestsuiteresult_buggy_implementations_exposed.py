# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0004_auto_20151204_0136'),
    ]

    operations = [
        migrations.AddField(
            model_name='studenttestsuiteresult',
            name='buggy_implementations_exposed',
            field=autograder.models.fields.StringListField(allow_empty_strings=False, strip_strings=False, size=None, default=[], string_validators=[]),
        ),
    ]
