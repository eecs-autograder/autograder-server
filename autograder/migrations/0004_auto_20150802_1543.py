# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0003_auto_20150731_1449'),
    ]

    operations = [
        migrations.AlterField(
            model_name='_uploadedprojectfile',
            name='project',
            field=models.ForeignKey(related_name='_project_files', to='autograder.Project'),
        ),
    ]
