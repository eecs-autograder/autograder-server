# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields
import autograder.shared.utilities


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='_requiredstudentfile',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='_requiredstudentfile',
            name='modelvalidatableonsave_ptr',
        ),
        migrations.RemoveField(
            model_name='_requiredstudentfile',
            name='project',
        ),
        migrations.AddField(
            model_name='project',
            name='required_student_files',
            field=django.contrib.postgres.fields.ArrayField(size=None, base_field=models.CharField(validators=[autograder.shared.utilities.check_user_provided_filename], max_length=255), default=[]),
        ),
        migrations.DeleteModel(
            name='_RequiredStudentFile',
        ),
    ]
