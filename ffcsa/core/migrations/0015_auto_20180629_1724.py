# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-06-30 00:24
from __future__ import unicode_literals

import cartridge.shop.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ffcsa_core', '0014_merge_20180629_1721'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='monthly_contribution',
            field=cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Monthly Contribution'),
        ),
    ]
