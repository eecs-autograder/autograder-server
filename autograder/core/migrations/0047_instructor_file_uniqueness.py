# Generated by Django 2.2 on 2019-06-27 14:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0046_instructor_file_ordering'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='instructorfile',
            unique_together={('name', 'project')},
        ),
    ]