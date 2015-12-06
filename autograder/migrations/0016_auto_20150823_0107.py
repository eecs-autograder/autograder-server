# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0015_autogradertestcasebase_student_resource_files'),
    ]

    operations = [
        migrations.RenameField(
            model_name='submission',
            old_name='invalid_reason',
            new_name='invalid_reason_or_error',
        ),
        migrations.AlterField(
            model_name='submission',
            name='status',
            field=models.CharField(default='received', max_length=255, choices=[('received', 'Received'), ('queued', 'Queued'), ('being_graded', 'Being graded'), ('finished_grading', 'Finished grading'), ('invalid', 'Invalid'), ('error', 'Error')]),
        ),
    ]
