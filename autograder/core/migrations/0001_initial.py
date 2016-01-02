# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-01-02 01:04
from __future__ import unicode_literals

import autograder.core.models.submission
import autograder.core.shared.feedback_configuration
import autograder.core.shared.utilities
import autograder.utilities.fields
from django.conf import settings
import django.contrib.postgres.fields
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import re


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='_SubmittedFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submitted_file', models.FileField(max_length=510, upload_to=autograder.core.models.submission._get_submission_file_upload_to_dir, validators=[autograder.core.models.submission._validate_filename])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AutograderTestCaseResult',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('return_code', models.IntegerField(default=None, null=True)),
                ('standard_output', models.TextField()),
                ('standard_error_output', models.TextField()),
                ('timed_out', models.BooleanField(default=False)),
                ('valgrind_return_code', models.IntegerField(default=None, null=True)),
                ('valgrind_output', models.TextField()),
                ('compilation_return_code', models.IntegerField(default=None, null=True)),
                ('compilation_standard_output', models.TextField()),
                ('compilation_standard_error_output', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('administrators', models.ManyToManyField(related_name='courses_is_admin_for', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('message', models.CharField(max_length=500)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PolymorphicModelValidatableOnSave',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('visible_to_students', models.BooleanField(default=False)),
                ('closing_time', models.DateTimeField(blank=True, default=None, null=True)),
                ('disallow_student_submissions', models.BooleanField(default=False)),
                ('allow_submissions_from_non_enrolled_students', models.BooleanField(default=False)),
                ('min_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('max_group_size', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('_uploaded_filenames', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, max_string_length=255, size=None, string_validators=[], strip_strings=True)),
                ('_required_student_files', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), blank=True, default=list, size=None)),
                ('_expected_student_file_patterns', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=list)),
            ],
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='semesters', to='core.Course')),
                ('enrolled_students', models.ManyToManyField(related_name='semesters_is_enrolled_in', to=settings.AUTH_USER_MODEL)),
                ('staff', models.ManyToManyField(related_name='semesters_is_staff_for', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='StudentTestSuiteResult',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('buggy_implementations_exposed', autograder.utilities.fields.ClassField(class_=set, default=set, editable=False)),
                ('detailed_results', autograder.utilities.fields.ClassField(blank=True, class_=list, default=list, editable=False)),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discarded_files', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('_timestamp', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('received', 'Received'), ('queued', 'Queued'), ('being_graded', 'Being graded'), ('finished_grading', 'Finished grading'), ('invalid', 'Invalid'), ('error', 'Error')], default='received', max_length=255)),
                ('invalid_reason_or_error', jsonfield.fields.JSONField(default=list)),
            ],
            options={
                'ordering': ['pk'],
            },
        ),
        migrations.CreateModel(
            name='SubmissionGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('extended_due_date', models.DateTimeField(blank=True, default=None, null=True)),
                ('members', models.ManyToManyField(related_name='groups_is_member_of', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submission_groups', to='core.Project')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SubmissionGroupInvitation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_invitees_who_accepted', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=list, max_string_length=255, size=None, string_validators=[], strip_strings=True)),
                ('invitation_creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_invitations_sent', to=settings.AUTH_USER_MODEL)),
                ('invited_users', models.ManyToManyField(related_name='group_invitations_received', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Project')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AutograderTestCaseBase',
            fields=[
                ('polymorphicmodelvalidatableonsave_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.PolymorphicModelValidatableOnSave')),
                ('name', autograder.utilities.fields.ShortStringField(max_length=255, strip=True)),
                ('command_line_arguments', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=list, max_string_length=255, size=None, string_validators=[django.core.validators.RegexValidator(re.compile('^[a-zA-Z0-9-_=.]+$', 32))], strip_strings=True)),
                ('standard_input', models.TextField(blank=True)),
                ('test_resource_files', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=[], max_string_length=255, size=None, string_validators=[], strip_strings=False)),
                ('student_resource_files', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=[], max_string_length=255, size=None, string_validators=[], strip_strings=False)),
                ('time_limit', models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(60)])),
                ('expected_return_code', models.IntegerField(blank=True, default=None, null=True)),
                ('expect_any_nonzero_return_code', models.BooleanField(default=False)),
                ('expected_standard_output', models.TextField(blank=True)),
                ('expected_standard_error_output', models.TextField(blank=True)),
                ('_use_valgrind', models.BooleanField(default=False)),
                ('valgrind_flags', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=None, max_string_length=255, null=True, size=None, string_validators=[django.core.validators.RegexValidator(re.compile('^[a-zA-Z0-9-_=.]+$', 32))], strip_strings=True)),
                ('points_for_correct_return_code', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_correct_output', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('deduction_for_valgrind_errors', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('points_for_compilation_success', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('feedback_configuration', autograder.utilities.fields.JsonSerializableClassField(class_=autograder.core.shared.feedback_configuration.AutograderTestCaseFeedbackConfiguration, default=autograder.core.shared.feedback_configuration.AutograderTestCaseFeedbackConfiguration)),
                ('post_deadline_final_submission_feedback_configuration', autograder.utilities.fields.JsonSerializableClassField(blank=True, class_=autograder.core.shared.feedback_configuration.AutograderTestCaseFeedbackConfiguration, default=None, null=True)),
            ],
            bases=('core.polymorphicmodelvalidatableonsave',),
        ),
        migrations.CreateModel(
            name='StudentTestSuiteBase',
            fields=[
                ('polymorphicmodelvalidatableonsave_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.PolymorphicModelValidatableOnSave')),
                ('name', models.CharField(max_length=255)),
                ('student_test_case_filename_pattern', models.CharField(max_length=255)),
                ('correct_implementation_filename', models.CharField(max_length=255)),
                ('buggy_implementation_filenames', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), blank=True, default=list, size=None)),
                ('implementation_file_alias', autograder.utilities.fields.ShortStringField(blank=True, max_length=255, strip=True, validators=[django.core.validators.RegexValidator(re.compile('[a-zA-Z][a-zA-Z0-9-_.]*|^$', 32))])),
                ('suite_resource_filenames', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), blank=True, default=list, size=None)),
                ('time_limit', models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(60)])),
                ('hide_from_students', models.BooleanField(default=True)),
                ('points_per_buggy_implementation_exposed', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('feedback_configuration', autograder.utilities.fields.JsonSerializableClassField(class_=autograder.core.shared.feedback_configuration.StudentTestSuiteFeedbackConfiguration, default=autograder.core.shared.feedback_configuration.StudentTestSuiteFeedbackConfiguration)),
                ('post_deadline_final_submission_feedback_configuration', autograder.utilities.fields.JsonSerializableClassField(blank=True, class_=autograder.core.shared.feedback_configuration.StudentTestSuiteFeedbackConfiguration, default=None, null=True)),
            ],
            bases=('core.polymorphicmodelvalidatableonsave',),
        ),
        migrations.AddField(
            model_name='submission',
            name='submission_group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='core.SubmissionGroup'),
        ),
        migrations.AddField(
            model_name='studenttestsuiteresult',
            name='submission',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='suite_results', to='core.Submission'),
        ),
        migrations.AddField(
            model_name='project',
            name='semester',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='projects', to='core.Semester'),
        ),
        migrations.AddField(
            model_name='polymorphicmodelvalidatableonsave',
            name='polymorphic_ctype',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='polymorphic_core.polymorphicmodelvalidatableonsave_set+', to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='autogradertestcaseresult',
            name='submission',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='results', to='core.Submission'),
        ),
        migrations.AddField(
            model_name='_submittedfile',
            name='submission',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='_submitted_files', to='core.Submission'),
        ),
        migrations.CreateModel(
            name='CompilationOnlyAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.AutograderTestCaseBase')),
                ('compiler', autograder.utilities.fields.ShortStringField(choices=[('g++', 'g++'), ('clang++', 'clang++'), ('gcc', 'gcc'), ('clang', 'clang')], max_length=255, strip=True)),
                ('compiler_flags', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=list, max_string_length=255, size=None, string_validators=[django.core.validators.RegexValidator(re.compile('^[a-zA-Z0-9-_=.]+$', 32))], strip_strings=True)),
                ('files_to_compile_together', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=list, max_string_length=255, size=None, string_validators=[], strip_strings=False)),
                ('executable_name', autograder.utilities.fields.ShortStringField(default='compiled_program', max_length=255, strip=True, validators=[autograder.core.shared.utilities.check_user_provided_filename])),
            ],
            options={
                'abstract': False,
            },
            bases=('core.autogradertestcasebase',),
        ),
        migrations.CreateModel(
            name='CompiledAndRunAutograderTestCase',
            fields=[
                ('autogradertestcasebase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.AutograderTestCaseBase')),
                ('compiler', autograder.utilities.fields.ShortStringField(choices=[('g++', 'g++'), ('clang++', 'clang++'), ('gcc', 'gcc'), ('clang', 'clang')], max_length=255, strip=True)),
                ('compiler_flags', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=list, max_string_length=255, size=None, string_validators=[django.core.validators.RegexValidator(re.compile('^[a-zA-Z0-9-_=.]+$', 32))], strip_strings=True)),
                ('files_to_compile_together', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=list, max_string_length=255, size=None, string_validators=[], strip_strings=False)),
                ('executable_name', autograder.utilities.fields.ShortStringField(default='compiled_program', max_length=255, strip=True, validators=[autograder.core.shared.utilities.check_user_provided_filename])),
            ],
            options={
                'abstract': False,
            },
            bases=('core.autogradertestcasebase',),
        ),
        migrations.CreateModel(
            name='CompiledStudentTestSuite',
            fields=[
                ('studenttestsuitebase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.StudentTestSuiteBase')),
                ('compiler', models.CharField(choices=[('g++', 'g++'), ('clang++', 'clang++'), ('gcc', 'gcc'), ('clang', 'clang')], max_length=255)),
                ('compiler_flags', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=list, max_string_length=255, size=None, string_validators=[django.core.validators.RegexValidator(re.compile('^[a-zA-Z0-9-_=.]+$', 32))], strip_strings=True)),
                ('suite_resource_files_to_compile_together', autograder.utilities.fields.StringArrayField(allow_empty_strings=False, blank=True, default=list, max_string_length=255, size=None, string_validators=[], strip_strings=True)),
                ('compile_implementation_files', models.BooleanField(default=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('core.studenttestsuitebase',),
        ),
        migrations.AddField(
            model_name='studenttestsuiteresult',
            name='test_suite',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.StudentTestSuiteBase'),
        ),
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_test_suites', to='core.Project'),
        ),
        migrations.AlterUniqueTogether(
            name='semester',
            unique_together=set([('name', 'course')]),
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together=set([('name', 'semester')]),
        ),
        migrations.AddField(
            model_name='autogradertestcaseresult',
            name='test_case',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.AutograderTestCaseBase'),
        ),
        migrations.AddField(
            model_name='autogradertestcasebase',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='autograder_test_cases', to='core.Project'),
        ),
        migrations.AlterUniqueTogether(
            name='studenttestsuitebase',
            unique_together=set([('name', 'project')]),
        ),
        migrations.AlterUniqueTogether(
            name='autogradertestcasebase',
            unique_together=set([('name', 'project')]),
        ),
    ]
