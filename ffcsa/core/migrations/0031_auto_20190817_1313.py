# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-08-17 20:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ffcsa_core', '0030_auto_20190817_1137'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='allow_substitutions',
            field=models.BooleanField(default=True, help_text='I am okay with substitutions when an item I ordered is no longer available. We do our best to pack what you have ordered, however on occasion crops will not be ready to harvest, etc. We can provide a substitution, or we can credit your account.'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='no_plastic_bags',
            field=models.BooleanField(default=False, help_text='Do not pack my items in a plastic bag when possible.'),
        ),
    ]