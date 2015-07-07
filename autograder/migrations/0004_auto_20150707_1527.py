# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.project
import autograder.shared.utilities


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0003_auto_20150707_1516'),
    ]

    operations = [
        migrations.CreateModel(
            name='_RequiredStudentFile',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', auto_created=True, serialize=False, primary_key=True)),
                ('filename', models.CharField(max_length=255, validators=[autograder.shared.utilities.check_user_provided_filename])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='_UploadedProjectFile',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(parent_link=True, to='autograder.ModelValidatableOnSave', auto_created=True, serialize=False, primary_key=True)),
                ('uploaded_file', models.FileField(upload_to=autograder.models.project._get_project_file_upload_to_dir, validators=[autograder.models.project._validate_filename])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.RemoveField(
            model_name='project',
            name='project_files',
        ),
        migrations.RemoveField(
            model_name='project',
            name='required_student_files',
        ),
        migrations.AddField(
            model_name='_uploadedprojectfile',
            name='project',
            field=models.ForeignKey(related_name='project_files', to='autograder.Project'),
        ),
        migrations.AddField(
            model_name='_requiredstudentfile',
            name='project',
            field=models.ForeignKey(related_name='required_student_files', to='autograder.Project'),
        ),
        migrations.AlterUniqueTogether(
            name='_requiredstudentfile',
            unique_together=set([('project', 'filename')]),
        ),
    ]
