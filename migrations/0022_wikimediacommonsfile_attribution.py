# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-03 20:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('superlachaise_api', '0021_auto_20160417_2209'),
    ]

    operations = [
        migrations.AddField(
            model_name='wikimediacommonsfile',
            name='attribution',
            field=models.CharField(blank=True, max_length=255, verbose_name='attribution'),
        ),
    ]