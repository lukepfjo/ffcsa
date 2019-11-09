# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-10-25 18:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def create_vendors(apps, schema_editor):
    Vendor = apps.get_model("shop", "Vendor")
    ProductVariation = apps.get_model("shop", "ProductVariation")
    VendorProductVariation = apps.get_model("shop", "VendorProductVariations")

    for pv in ProductVariation.objects.all():
        if not pv.vendor:
            continue
        v, created = Vendor.objects.get_or_create(title=pv.vendor.title(), defaults={'site_id': pv.product.site.id})
        VendorProductVariation.objects.create(variation=pv, vendor_id=v.id, num_in_stock=pv.num_in_stock)


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0026_auto_20191024_1859'),
    ]

    operations = [
        migrations.CreateModel(
            name='VendorProductVariations',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('num_in_stock', models.IntegerField(blank=True, null=True, verbose_name='Number in stock')),
            ],
        ),
        migrations.AddField(
            model_name='vendorproductvariations',
            name='variation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shop.ProductVariation',
                                    verbose_name='variation'),
        ),
        migrations.AddField(
            model_name='vendorproductvariations',
            name='vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shop.Vendor',
                                    verbose_name='Vendor'),
        ),
        migrations.AddField(
            model_name='productvariation',
            name='vendors',
            field=models.ManyToManyField(related_name='variations', through='shop.VendorProductVariations',
                                         to='shop.Vendor', verbose_name='Vendors'),
        ),
        migrations.RunPython(create_vendors),
        migrations.RemoveField(
            model_name='productvariation',
            name='vendor',
        ),
    ]
