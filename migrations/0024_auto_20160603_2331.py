# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-03 21:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('superlachaise_api', '0023_auto_20160603_2251'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wikimediacommonsfile',
            name='license',
            field=models.CharField(blank=True, db_index=True, max_length=255, verbose_name='license'),
        ),
    ]