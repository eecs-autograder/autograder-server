# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0005_studenttestsuiteresult_buggy_implementations_exposed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuiteresult',
            name='buggy_implementations_exposed',
            field=autograder.models.fields.ClassField(class_=set, editable=False),
        ),
    ]
