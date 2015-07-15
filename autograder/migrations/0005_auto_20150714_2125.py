# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0004_auto_20150714_2039'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='_expectedstudentfilepattern',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='_expectedstudentfilepattern',
            name='modelvalidatableonsave_ptr',
        ),
        migrations.RemoveField(
            model_name='_expectedstudentfilepattern',
            name='project',
        ),
        migrations.AddField(
            model_name='project',
            name='expected_student_file_patterns',
            field=jsonfield.fields.JSONField(blank=True, default=[]),
        ),
        migrations.DeleteModel(
            name='_ExpectedStudentFilePattern',
        ),
    ]
