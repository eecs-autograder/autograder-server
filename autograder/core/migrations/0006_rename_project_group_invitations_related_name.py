# Generated by Django 2.0.1 on 2018-04-27 20:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_rename_group_project_related_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupinvitation',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_invitations', to='core.Project'),
        ),
    ]
