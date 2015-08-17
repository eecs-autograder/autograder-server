# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0012_auto_20150815_1438'),
    ]

    operations = [
        migrations.RenameField(
            model_name='autogradertestcaseresultbase',
            old_name='_compilation_return_code',
            new_name='compilation_return_code',
        ),
        migrations.RenameField(
            model_name='autogradertestcaseresultbase',
            old_name='_compilation_standard_error_output',
            new_name='compilation_standard_error_output',
        ),
        migrations.RenameField(
            model_name='autogradertestcaseresultbase',
            old_name='_compilation_standard_output',
            new_name='compilation_standard_output',
        ),
        migrations.RenameField(
            model_name='autogradertestcaseresultbase',
            old_name='_return_code',
            new_name='return_code',
        ),
        migrations.RenameField(
            model_name='autogradertestcaseresultbase',
            old_name='_standard_error_output',
            new_name='standard_error_output',
        ),
        migrations.RenameField(
            model_name='autogradertestcaseresultbase',
            old_name='_standard_output',
            new_name='standard_output',
        ),
        migrations.RenameField(
            model_name='autogradertestcaseresultbase',
            old_name='_timed_out',
            new_name='timed_out',
        ),
        migrations.RenameField(
            model_name='autogradertestcaseresultbase',
            old_name='_valgrind_output',
            new_name='valgrind_output',
        ),
        migrations.RenameField(
            model_name='autogradertestcaseresultbase',
            old_name='_valgrind_return_code',
            new_name='valgrind_return_code',
        ),
    ]
