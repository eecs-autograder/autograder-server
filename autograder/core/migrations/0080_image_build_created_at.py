# Generated by Django 2.2.12 on 2020-06-08 19:37

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0079_image_to_update_cascade_delete'),
    ]

    operations = [
        migrations.AddField(
            model_name='buildsandboxdockerimagetask',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]