# Generated by Django 3.2.7 on 2021-09-26 02:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0017_alter_credit_role'),
    ]

    operations = [
        migrations.RenameField(
            model_name='book',
            old_name='authors',
            new_name='credits',
        ),
    ]
