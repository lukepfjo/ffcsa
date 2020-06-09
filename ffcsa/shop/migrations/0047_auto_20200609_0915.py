# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2020-06-09 16:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0046_auto_20200422_1223'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='in_inventory',
            field=models.BooleanField(default=False, help_text='Is this product already purchased and we do not need to place an order? If so, this should be checked', verbose_name='FFCSA Inventory'),
        ),
        migrations.AlterField(
            model_name='product',
            name='weekly_inventory',
            field=models.BooleanField(default=False, help_text='Does the “number in stock” for this product reset each week? If so, this should be checked.', verbose_name='Weekly Inventory'),
        ),
        migrations.AlterField(
            model_name='productvariation',
            name='extra',
            field=models.IntegerField(blank=True, help_text='The % extra to order. This is used when a product is sold by the #, but it is difficult to weigh exactly to the # during pack out. The larger the item, the higher this % should be. The extra ordered will be rounded to the nearest whole number.', null=True, verbose_name='% Extra'),
        ),
        migrations.AlterField(
            model_name='productvariation',
            name='in_inventory',
            field=models.BooleanField(default=False, help_text='Is this product already purchased and we do not need to place an order? If so, this should be checked', verbose_name='FFCSA Inventory'),
        ),
        migrations.AlterField(
            model_name='productvariation',
            name='is_frozen',
            field=models.BooleanField(default=False, help_text='Is this product frozen and should be packed with other frozen items into a cooler?'),
        ),
        migrations.AlterField(
            model_name='productvariation',
            name='weekly_inventory',
            field=models.BooleanField(default=False, help_text='Does the “number in stock” for this product reset each week? If so, this should be checked.', verbose_name='Weekly Inventory'),
        ),
    ]
