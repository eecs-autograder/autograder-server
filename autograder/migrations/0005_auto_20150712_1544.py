# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0004_auto_20150711_1648'),
    ]

    operations = [
        migrations.AlterField(
            model_name='semester',
            name='course',
            field=models.ForeignKey(to='autograder.Course', related_name='semesters'),
        ),
    ]
