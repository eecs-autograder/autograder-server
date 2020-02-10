# Generated by Django 2.2.4 on 2020-02-10 19:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0053_auto_20200121_2119'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sandboxdockerimage',
            name='tag',
            field=models.TextField(help_text="The full name and tag that can be used to fetch the image\n                     with the 'docker pull' command, e.g. jameslp/eecs280:2.\n                     This should include a specific\n                     version for the image, and the version number should be\n                     incremented by the user every time the image is updated,\n                     otherwise the new version of the image will not be\n                     fetched."),
        ),
    ]
