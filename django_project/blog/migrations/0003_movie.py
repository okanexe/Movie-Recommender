# Generated by Django 3.0.7 on 2020-06-25 13:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0002_profile'),
    ]

    operations = [
        migrations.CreateModel(
            name='Movie',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imdb_id', models.CharField(max_length=1500)),
                ('title', models.CharField(max_length=2000)),
                ('overview', models.CharField(max_length=20000)),
                ('genre', models.CharField(max_length=4000)),
            ],
        ),
    ]
