# Generated by Django 3.2.7 on 2021-09-24 23:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0014_rename_authorship_credit'),
    ]

    operations = [
        migrations.AddField(
            model_name='credit',
            name='role',
            field=models.CharField(choices=[('author', 'Author')], default='author', max_length=16),
        ),
    ]