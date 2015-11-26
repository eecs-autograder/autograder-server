# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0023_auto_20150914_2113'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentTestSuiteBase',
            fields=[
                ('polymorphicmodelvalidatableonsave_ptr', models.OneToOneField(auto_created=True, parent_link=True, primary_key=True, to='autograder.PolymorphicModelValidatableOnSave', serialize=False)),
            ],
            options={
                'abstract': False,
            },
            bases=('autograder.polymorphicmodelvalidatableonsave',),
        ),
    ]
