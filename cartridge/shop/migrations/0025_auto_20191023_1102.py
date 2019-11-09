# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-10-23 18:02
from __future__ import unicode_literals

import cartridge.shop.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0024_auto_20191011_0826'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartitem',
            name='vendor_price',
            field=cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Vendor price'),
        ),
        migrations.AlterField(
            model_name='order',
            name='allow_substitutions',
            field=models.BooleanField(default=False, verbose_name='Allow product substitutions'),
        ),
        migrations.AlterField(
            model_name='order',
            name='billing_detail_phone_2',
            field=models.CharField(blank=True, max_length=20, verbose_name='Alt. Phone'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='vendor_price',
            field=cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Vendor price'),
        ),
        migrations.AlterField(
            model_name='product',
            name='order_on_invoice',
            field=models.FloatField(blank=True, default=0, help_text="Order this product will be printed on invoices. If set, this will override the product's category order_on_invoice setting. This is a float number for more fine grained control. (ex. '2.1' will be sorted the same as if the product's parent category order_on_invoice was 2 & the product's category order_on_invoice was 1).", null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='vendor_price',
            field=cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Vendor price'),
        ),
        migrations.AlterField(
            model_name='productvariation',
            name='vendor_price',
            field=cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Vendor price'),
        ),
    ]
