# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-05-14 02:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('test_models', '0003__dummyautogradermodel_read_only_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='_dummyautogradermodel',
            name='read_only_field',
            field=models.TextField(blank=True),
        ),
    ]