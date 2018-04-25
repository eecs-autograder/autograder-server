import django
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0021_rename_staff_and_admin_fields'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='UploadedFile',
            new_name='InstructorFile',
        ),

      migrations.AlterField(
            model_name='agcommand',
            name='stdin_project_file',
            field=models.ForeignKey(blank=True, default=None, help_text='An InstructorFile whose contents should be redirected to the stdin of this\n                     command. This value is used when stdin_source is StdinSource.project_file\n                     and is ignored otherwise.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.InstructorFile'),
        ),
        migrations.AlterField(
            model_name='agtestcommand',
            name='expected_stderr_project_file',
            field=models.ForeignKey(blank=True, default=None, help_text="An InstructorFile whose contents should be compared against this command's\n                     stderr. This value is used (and may not be null) when expected_stderr_source\n                     is ExpectedOutputSource.project_file and is ignored otherwise.", null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.InstructorFile'),
        ),
        migrations.AlterField(
            model_name='agtestcommand',
            name='expected_stdout_project_file',
            field=models.ForeignKey(blank=True, default=None, help_text="An InstructorFile whose contents should be compared against this command's\n                     stdout. This value is used (and may not be null) when expected_stdout_source\n                     is ExpectedOutputSource.project_file and is ignored otherwise.", null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.InstructorFile'),
        ),
        migrations.AlterField(
            model_name='agtestcommand',
            name='stdin_project_file',
            field=models.ForeignKey(blank=True, default=None, help_text='An InstructorFile whose contents should be redirected to the stdin of this\n                     command. This value is used when stdin_source is StdinSource.project_file\n                     and is ignored otherwise.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.InstructorFile'),
        ),
        migrations.AlterField(
            model_name='course',
            name='admins',
            field=models.ManyToManyField(help_text='The Users that are admins for\n                  this Course. admins have edit access\n                  to this Course.', related_name='courses_is_admin_for', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='instructorfile',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='instructor_files', to='core.Project'),
        ),
    ]
