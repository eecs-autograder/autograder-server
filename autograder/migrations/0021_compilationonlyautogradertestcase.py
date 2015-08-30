# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0020_auto_20150829_0300'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompilationOnlyAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(auto_created=True, serialize=False, to='autograder.AutograderTestCaseBase', parent_link=True, primary_key=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.autogradertestcasebase',),
        ),
    ]
