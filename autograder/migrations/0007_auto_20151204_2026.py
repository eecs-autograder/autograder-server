# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0006_auto_20151204_1832'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuiteresult',
            name='buggy_implementations_exposed',
            field=autograder.models.fields.ClassField(editable=False, default=set, class_=set),
        ),
    ]
