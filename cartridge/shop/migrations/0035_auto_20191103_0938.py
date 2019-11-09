# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-11-03 17:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0034_auto_20191102_1718'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productvariation',
            name='_title',
            field=models.CharField(blank=True, max_length=500, verbose_name='Title'),
        ),
        migrations.AlterOrderWithRespectTo(
            name='vendorcartitem',
            order_with_respect_to='item',
        ),
    ]
