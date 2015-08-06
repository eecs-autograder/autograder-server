# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0005_project_allow_submissions_from_non_enrolled_students'),
    ]

    operations = [
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='points_for_compilation_success',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='points_for_correct_output',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='points_for_correct_return_code',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='points_for_no_valgrind_errors',
            field=models.IntegerField(default=0),
        ),
    ]
