# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-01-02 01:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='_DummyStudentTestSuite',
            fields=[
                ('studenttestsuitebase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.StudentTestSuiteBase')),
            ],
            options={
                'abstract': False,
            },
            bases=('core.studenttestsuitebase',),
        ),
    ]
