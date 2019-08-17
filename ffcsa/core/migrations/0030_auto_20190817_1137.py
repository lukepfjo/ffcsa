# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-08-17 18:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ffcsa_core', '0029_auto_20190625_0604'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='allow_substitutions',
            field=models.BooleanField(default=True, help_text='I am okay with substitutions when an item I ordered is no longer available.'),
        ),
        migrations.AddField(
            model_name='profile',
            name='no_plastic_bags',
            field=models.BooleanField(default=False, help_text='Do not pack items in a plastic bag when possible.'),
        ),
    ]
