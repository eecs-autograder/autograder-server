from django.contrib.auth.models import User

users = []

for i in range(10):
    user = User(
        firstName='firstname{}'.format(i),
        lastName='lastname{}'.format(i),
        username='user{}'.format(i),
        email='jameslp@umich.edu')
    user.set_password('password{}'.format(i))
    users.append(user)

User.objects.bulk_create(users)
