# Generated by Django 3.0.7 on 2020-06-29 13:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_profile_usersurl'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='usersURL',
        ),
    ]