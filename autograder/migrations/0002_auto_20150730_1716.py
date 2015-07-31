# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='semester',
            old_name='_enrolled_students',
            new_name='_enrolled_student_names',
        ),
    ]
