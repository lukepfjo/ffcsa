# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2020-03-25 18:28
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ffcsa_core', '0042_auto_20200323_0545'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='num_adults',
            field=models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='How many adults are in your family?'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profile',
            name='signed_membership_agreement',
            field=models.BooleanField(default=False, help_text='We have a signed Member Liability Document of file.'),
        ),
    ]