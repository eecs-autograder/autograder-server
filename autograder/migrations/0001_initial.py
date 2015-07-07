# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import autograder.models.project
import django.core.validators
import autograder.shared.utilities


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ModelValidatableOnSave',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='_ExpectedStudentFilePattern',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(serialize=False, auto_created=True, to='autograder.ModelValidatableOnSave', primary_key=True, parent_link=True)),
                ('pattern', models.CharField(validators=[autograder.shared.utilities.check_shell_style_file_pattern], max_length=255)),
                ('min_num_matches', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('max_num_matches', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='_RequiredStudentFile',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(serialize=False, auto_created=True, to='autograder.ModelValidatableOnSave', primary_key=True, parent_link=True)),
                ('filename', models.CharField(validators=[autograder.shared.utilities.check_user_provided_filename], max_length=255)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='_UploadedProjectFile',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(serialize=False, auto_created=True, to='autograder.ModelValidatableOnSave', primary_key=True, parent_link=True)),
                ('uploaded_file', models.FileField(validators=[autograder.models.project._validate_filename], upload_to=autograder.models.project._get_project_file_upload_to_dir)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(auto_created=True, to='autograder.ModelValidatableOnSave', parent_link=True)),
                ('name', models.CharField(max_length=255, serialize=False, primary_key=True)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(serialize=False, auto_created=True, to='autograder.ModelValidatableOnSave', primary_key=True, parent_link=True)),
                ('name', models.CharField(max_length=255)),
                ('visible_to_students', models.BooleanField(default=False)),
                ('closing_time', models.DateTimeField(blank=True, null=True, default=None)),
                ('disallow_student_submissions', models.BooleanField(default=False)),
                ('min_group_size', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], default=1)),
                ('max_group_size', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], default=1)),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(serialize=False, auto_created=True, to='autograder.ModelValidatableOnSave', primary_key=True, parent_link=True)),
                ('name', models.CharField(max_length=255)),
                ('course', models.ForeignKey(to='autograder.Course')),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='SubmissionGroup',
            fields=[
                ('modelvalidatableonsave_ptr', models.OneToOneField(serialize=False, auto_created=True, to='autograder.ModelValidatableOnSave', primary_key=True, parent_link=True)),
                ('extended_due_date', models.DateTimeField(blank=True, null=True, default=None)),
                ('members', models.ManyToManyField(related_name='submission_groups', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(to='autograder.Project')),
            ],
            bases=('autograder.modelvalidatableonsave',),
        ),
        migrations.AddField(
            model_name='project',
            name='semester',
            field=models.ForeignKey(to='autograder.Semester'),
        ),
        migrations.AddField(
            model_name='_uploadedprojectfile',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='project_files'),
        ),
        migrations.AddField(
            model_name='_requiredstudentfile',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='required_student_files'),
        ),
        migrations.AddField(
            model_name='_expectedstudentfilepattern',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='expected_student_file_patterns'),
        ),
        migrations.AlterUniqueTogether(
            name='semester',
            unique_together=set([('name', 'course')]),
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together=set([('name', 'semester')]),
        ),
        migrations.AlterUniqueTogether(
            name='_requiredstudentfile',
            unique_together=set([('project', 'filename')]),
        ),
        migrations.AlterUniqueTogether(
            name='_expectedstudentfilepattern',
            unique_together=set([('project', 'pattern')]),
        ),
    ]
