# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0005_auto_20150809_1941'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='invalid_reason',
            field=jsonfield.fields.JSONField(default=list),
        ),
    ]
