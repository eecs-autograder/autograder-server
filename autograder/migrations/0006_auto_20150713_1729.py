# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0005_auto_20150712_1544'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='semester',
            field=models.ForeignKey(to='autograder.Semester', related_name='projects'),
        ),
    ]
