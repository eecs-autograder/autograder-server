# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0021_compilationonlyautogradertestcase'),
    ]

    operations = [
        migrations.RenameField(
            model_name='project',
            old_name='required_student_files',
            new_name='_required_student_files',
        ),
    ]
