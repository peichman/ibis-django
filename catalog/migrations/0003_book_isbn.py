# Generated by Django 3.2.7 on 2021-09-17 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_book_author'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='isbn',
            field=models.CharField(default='TBD', max_length=13),
            preserve_default=False,
        ),
    ]
