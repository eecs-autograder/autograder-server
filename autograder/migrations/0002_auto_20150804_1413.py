# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('autograder', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PolymorphicModelValidatableOnSave',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('polymorphic_ctype', models.ForeignKey(related_name='polymorphic_autograder.polymorphicmodelvalidatableonsave_set+', editable=False, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='autogradertestcasebase',
            name='id',
        ),
        migrations.RemoveField(
            model_name='autogradertestcasebase',
            name='polymorphic_ctype',
        ),
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='polymorphicmodelvalidatableonsave_ptr',
            field=models.OneToOneField(parent_link=True, primary_key=True, default=42, serialize=False, to='autograder.PolymorphicModelValidatableOnSave', auto_created=True),
            preserve_default=False,
        ),
    ]
