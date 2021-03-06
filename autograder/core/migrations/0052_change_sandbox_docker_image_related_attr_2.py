# Generated by Django 2.2.4 on 2020-01-21 20:40

import autograder.core.models.sandbox_docker_image
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_change_sandbox_docker_image_related_attr_1'),
    ]

    operations = [
        migrations.AddField(
            model_name='agtestsuite',
            name='new_sandbox_docker_image',
            field=models.ForeignKey(default=autograder.core.models.sandbox_docker_image.get_default_image_pk, help_text='The sandbox docker image to use for running this suite.', on_delete=models.SET(autograder.core.models.sandbox_docker_image.get_default_image_pk), related_name='+', to='core.SandboxDockerImage'),
        ),
        migrations.AddField(
            model_name='studenttestsuite',
            name='new_sandbox_docker_image',
            field=models.ForeignKey(default=autograder.core.models.sandbox_docker_image.get_default_image_pk, help_text='The sandbox docker image to use for running this suite.', on_delete=models.SET(autograder.core.models.sandbox_docker_image.get_default_image_pk), related_name='+', to='core.SandboxDockerImage'),
        ),
    ]
