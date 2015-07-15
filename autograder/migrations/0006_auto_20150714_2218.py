# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0005_auto_20150714_2125'),
    ]

    operations = [
        migrations.RenameField(
            model_name='project',
            old_name='expected_student_file_patterns',
            new_name='_expected_student_file_patterns',
        ),
    ]
