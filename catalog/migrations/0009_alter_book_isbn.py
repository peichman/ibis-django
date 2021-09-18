# Generated by Django 3.2.7 on 2021-09-18 17:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_alter_book_isbn'),
    ]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='isbn',
            field=models.CharField(blank=True, default='', max_length=13, verbose_name='ISBN'),
            preserve_default=False,
        ),
    ]
