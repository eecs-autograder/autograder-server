# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-12-21 21:55
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handgrading', '0004_handgradingresult_finished_grading'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='annotation',
            name='points',
        ),
        migrations.AddField(
            model_name='annotation',
            name='deduction',
            field=models.FloatField(blank=True, default=0, validators=[django.core.validators.MaxValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='annotation',
            name='max_deduction',
            field=models.FloatField(blank=True, default=None, null=True, validators=[django.core.validators.MaxValueValidator(0)]),
        ),
    ]
