# Generated by Django 3.2.7 on 2021-09-24 23:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0015_credit_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='credit',
            name='role',
            field=models.CharField(choices=[('author', 'Author'), ('editor', 'Editor'), ('translator', 'Translator')], default='author', max_length=16),
        ),
    ]