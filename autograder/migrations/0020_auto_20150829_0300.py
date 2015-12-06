# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0019_auto_20150823_1426'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='compiledautogradertestcaseresult',
            name='autogradertestcaseresultbase_ptr',
        ),
        migrations.DeleteModel(
            name='CompiledAutograderTestCaseResult',
        ),
    ]
