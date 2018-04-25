from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0020_course_handgraders'),
    ]

    operations = [
        migrations.RenameField(
            model_name='course',
            old_name='enrolled_students',
            new_name='students',
        ),
        migrations.RenameField(
            model_name='course',
            old_name='administrators',
            new_name='admins',
        ),
    ]
