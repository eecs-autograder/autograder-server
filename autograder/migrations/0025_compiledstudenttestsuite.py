# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0024_studenttestsuitebase'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompiledStudentTestSuite',
            fields=[
                ('studenttestsuitebase_ptr', models.OneToOneField(parent_link=True, to='autograder.StudentTestSuiteBase', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.studenttestsuitebase',),
        ),
    ]
