# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-23 00:09
from __future__ import unicode_literals

import cartridge.shop.fields
from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion
import mezzanine.core.fields
import mezzanine.utils.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('pages', '0003_auto_20150527_1555'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_updated', models.DateTimeField(null=True, verbose_name='Last updated')),
            ],
        ),
        migrations.CreateModel(
            name='CartItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sku', cartridge.shop.fields.SKUField(max_length=20, verbose_name='SKU')),
                ('description', models.CharField(max_length=2000, verbose_name='Description')),
                ('quantity', models.IntegerField(default=0, verbose_name='Quantity')),
                ('unit_price', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, default=Decimal('0'), max_digits=10, null=True, verbose_name='Unit price')),
                ('total_price', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, default=Decimal('0'), max_digits=10, null=True, verbose_name='Total price')),
                ('url', models.CharField(max_length=2000)),
                ('image', models.CharField(max_length=200, null=True)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='shop.Cart')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='pages.Page')),
                ('content', mezzanine.core.fields.RichTextField(verbose_name='Content')),
                ('featured_image', mezzanine.core.fields.FileField(blank=True, max_length=255, null=True, verbose_name='Featured Image')),
                ('price_min', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Minimum price')),
                ('price_max', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Maximum price')),
                ('combined', models.BooleanField(default=True, help_text='If checked, products must match all specified filters, otherwise products can match any specified filter.', verbose_name='Combined')),
            ],
            options={
                'verbose_name_plural': 'Product categories',
                'ordering': ('_order',),
                'verbose_name': 'Product category',
            },
            bases=('pages.page', models.Model),
        ),
        migrations.CreateModel(
            name='DiscountCode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                ('active', models.BooleanField(default=False, verbose_name='Active')),
                ('discount_deduct', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Reduce by amount')),
                ('discount_percent', cartridge.shop.fields.PercentageField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Reduce by percent')),
                ('discount_exact', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Reduce to amount')),
                ('valid_from', models.DateTimeField(blank=True, null=True, verbose_name='Valid from')),
                ('valid_to', models.DateTimeField(blank=True, null=True, verbose_name='Valid to')),
                ('code', cartridge.shop.fields.DiscountCodeField(max_length=20, unique=True, verbose_name='Code')),
                ('min_purchase', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Minimum total purchase')),
                ('free_shipping', models.BooleanField(default=False, verbose_name='Free shipping')),
                ('uses_remaining', models.IntegerField(blank=True, help_text='If you wish to limit the number of times a code may be used, set this value. It will be decremented upon each use.', null=True, verbose_name='Uses remaining')),
                ('categories', models.ManyToManyField(blank=True, related_name='discountcode_related', to='shop.Category', verbose_name='Categories')),
            ],
            options={
                'verbose_name_plural': 'Discount codes',
                'verbose_name': 'Discount code',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('billing_detail_first_name', models.CharField(max_length=100, verbose_name='First name')),
                ('billing_detail_last_name', models.CharField(max_length=100, verbose_name='Last name')),
                ('billing_detail_street', models.CharField(max_length=100, verbose_name='Street')),
                ('billing_detail_city', models.CharField(max_length=100, verbose_name='City/Suburb')),
                ('billing_detail_state', models.CharField(max_length=100, verbose_name='State/Region')),
                ('billing_detail_postcode', models.CharField(max_length=10, verbose_name='Zip/Postcode')),
                ('billing_detail_country', models.CharField(max_length=100, verbose_name='Country')),
                ('billing_detail_phone', models.CharField(max_length=20, verbose_name='Phone')),
                ('billing_detail_email', models.EmailField(max_length=254, verbose_name='Email')),
                ('shipping_detail_first_name', models.CharField(max_length=100, verbose_name='First name')),
                ('shipping_detail_last_name', models.CharField(max_length=100, verbose_name='Last name')),
                ('shipping_detail_street', models.CharField(max_length=100, verbose_name='Street')),
                ('shipping_detail_city', models.CharField(max_length=100, verbose_name='City/Suburb')),
                ('shipping_detail_state', models.CharField(max_length=100, verbose_name='State/Region')),
                ('shipping_detail_postcode', models.CharField(max_length=10, verbose_name='Zip/Postcode')),
                ('shipping_detail_country', models.CharField(max_length=100, verbose_name='Country')),
                ('shipping_detail_phone', models.CharField(max_length=20, verbose_name='Phone')),
                ('additional_instructions', models.TextField(blank=True, verbose_name='Additional instructions')),
                ('time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Time')),
                ('key', models.CharField(db_index=True, max_length=40)),
                ('user_id', models.IntegerField(blank=True, null=True)),
                ('shipping_type', models.CharField(blank=True, max_length=50, verbose_name='Shipping type')),
                ('shipping_total', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Shipping total')),
                ('tax_type', models.CharField(blank=True, max_length=50, verbose_name='Tax type')),
                ('tax_total', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Tax total')),
                ('item_total', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Item total')),
                ('discount_code', cartridge.shop.fields.DiscountCodeField(blank=True, max_length=20, verbose_name='Discount code')),
                ('discount_total', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Discount total')),
                ('total', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Order total')),
                ('transaction_id', models.CharField(blank=True, max_length=255, null=True, verbose_name='Transaction ID')),
                ('status', models.IntegerField(choices=[(1, 'Unprocessed'), (2, 'Processed')], default=1, verbose_name='Status')),
                ('site', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='sites.Site')),
            ],
            options={
                'verbose_name_plural': 'Orders',
                'ordering': ('-id',),
                'verbose_name': 'Order',
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sku', cartridge.shop.fields.SKUField(max_length=20, verbose_name='SKU')),
                ('description', models.CharField(max_length=2000, verbose_name='Description')),
                ('quantity', models.IntegerField(default=0, verbose_name='Quantity')),
                ('unit_price', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, default=Decimal('0'), max_digits=10, null=True, verbose_name='Unit price')),
                ('total_price', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, default=Decimal('0'), max_digits=10, null=True, verbose_name='Total price')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='shop.Order')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keywords_string', models.CharField(blank=True, editable=False, max_length=500)),
                ('rating_count', models.IntegerField(default=0, editable=False)),
                ('rating_sum', models.IntegerField(default=0, editable=False)),
                ('rating_average', models.FloatField(default=0, editable=False)),
                ('title', models.CharField(max_length=500, verbose_name='Title')),
                ('slug', models.CharField(blank=True, help_text='Leave blank to have the URL auto-generated from the title.', max_length=2000, null=True, verbose_name='URL')),
                ('_meta_title', models.CharField(blank=True, help_text='Optional title to be used in the HTML title tag. If left blank, the main title field will be used.', max_length=500, null=True, verbose_name='Title')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('gen_description', models.BooleanField(default=True, help_text='If checked, the description will be automatically generated from content. Uncheck if you want to manually set a custom description.', verbose_name='Generate description')),
                ('created', models.DateTimeField(editable=False, null=True)),
                ('updated', models.DateTimeField(editable=False, null=True)),
                ('status', models.IntegerField(choices=[(1, 'Draft'), (2, 'Published')], default=2, help_text='With Draft chosen, will only be shown for admin users on the site.', verbose_name='Status')),
                ('publish_date', models.DateTimeField(blank=True, db_index=True, help_text="With Published chosen, won't be shown until this time", null=True, verbose_name='Published from')),
                ('expiry_date', models.DateTimeField(blank=True, help_text="With Published chosen, won't be shown after this time", null=True, verbose_name='Expires on')),
                ('short_url', models.URLField(blank=True, null=True)),
                ('in_sitemap', models.BooleanField(default=True, verbose_name='Show in sitemap')),
                ('content', mezzanine.core.fields.RichTextField(verbose_name='Content')),
                ('unit_price', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Unit price')),
                ('sale_id', models.IntegerField(null=True)),
                ('sale_price', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Sale price')),
                ('sale_from', models.DateTimeField(blank=True, null=True, verbose_name='Sale start')),
                ('sale_to', models.DateTimeField(blank=True, null=True, verbose_name='Sale end')),
                ('sku', cartridge.shop.fields.SKUField(blank=True, max_length=20, null=True, verbose_name='SKU')),
                ('num_in_stock', models.IntegerField(blank=True, null=True, verbose_name='Number in stock')),
                ('available', models.BooleanField(default=False, verbose_name='Available for purchase')),
                ('image', models.CharField(blank=True, max_length=100, null=True, verbose_name='Image')),
                ('date_added', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date added')),
                ('categories', models.ManyToManyField(blank=True, to='shop.Category', verbose_name='Product categories')),
                ('related_products', models.ManyToManyField(blank=True, related_name='_product_related_products_+', to='shop.Product', verbose_name='Related products')),
                ('site', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='sites.Site')),
                ('upsell_products', models.ManyToManyField(blank=True, related_name='_product_upsell_products_+', to='shop.Product', verbose_name='Upsell products')),
            ],
            options={
                'verbose_name_plural': 'Products',
                'verbose_name': 'Product',
            },
            bases=(models.Model, mezzanine.utils.models.AdminThumbMixin),
        ),
        migrations.CreateModel(
            name='ProductAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.IntegerField()),
                ('total_cart', models.IntegerField(default=0)),
                ('total_purchase', models.IntegerField(default=0)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actions', to='shop.Product')),
            ],
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_order', mezzanine.core.fields.OrderField(null=True, verbose_name='Order')),
                ('file', mezzanine.core.fields.FileField(max_length=255, verbose_name='Image')),
                ('description', models.CharField(blank=True, max_length=100, verbose_name='Description')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='shop.Product')),
            ],
            options={
                'verbose_name_plural': 'Images',
                'ordering': ('_order',),
                'verbose_name': 'Image',
            },
        ),
        migrations.CreateModel(
            name='ProductOption',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.IntegerField(choices=[(1, 'Size'), (2, 'Colour')], verbose_name='Type')),
                ('name', cartridge.shop.fields.OptionField(max_length=50, null=True, verbose_name='Name')),
            ],
            options={
                'verbose_name_plural': 'Product options',
                'verbose_name': 'Product option',
            },
        ),
        migrations.CreateModel(
            name='ProductVariation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unit_price', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Unit price')),
                ('sale_id', models.IntegerField(null=True)),
                ('sale_price', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Sale price')),
                ('sale_from', models.DateTimeField(blank=True, null=True, verbose_name='Sale start')),
                ('sale_to', models.DateTimeField(blank=True, null=True, verbose_name='Sale end')),
                ('sku', cartridge.shop.fields.SKUField(blank=True, max_length=20, null=True, verbose_name='SKU')),
                ('num_in_stock', models.IntegerField(blank=True, null=True, verbose_name='Number in stock')),
                ('default', models.BooleanField(default=False, verbose_name='Default')),
                ('option1', cartridge.shop.fields.OptionField(max_length=50, null=True, verbose_name='Size')),
                ('option2', cartridge.shop.fields.OptionField(max_length=50, null=True, verbose_name='Colour')),
                ('image', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='shop.ProductImage', verbose_name='Image')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variations', to='shop.Product')),
            ],
            options={
                'ordering': ('-default',),
            },
        ),
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                ('active', models.BooleanField(default=False, verbose_name='Active')),
                ('discount_deduct', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Reduce by amount')),
                ('discount_percent', cartridge.shop.fields.PercentageField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Reduce by percent')),
                ('discount_exact', cartridge.shop.fields.MoneyField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Reduce to amount')),
                ('valid_from', models.DateTimeField(blank=True, null=True, verbose_name='Valid from')),
                ('valid_to', models.DateTimeField(blank=True, null=True, verbose_name='Valid to')),
                ('categories', models.ManyToManyField(blank=True, related_name='sale_related', to='shop.Category', verbose_name='Categories')),
                ('products', models.ManyToManyField(blank=True, to='shop.Product', verbose_name='Products')),
            ],
            options={
                'verbose_name_plural': 'Sales',
                'verbose_name': 'Sale',
            },
        ),
        migrations.AddField(
            model_name='discountcode',
            name='products',
            field=models.ManyToManyField(blank=True, to='shop.Product', verbose_name='Products'),
        ),
        migrations.AddField(
            model_name='category',
            name='options',
            field=models.ManyToManyField(blank=True, related_name='product_options', to='shop.ProductOption', verbose_name='Product options'),
        ),
        migrations.AddField(
            model_name='category',
            name='products',
            field=models.ManyToManyField(blank=True, to='shop.Product', verbose_name='Products'),
        ),
        migrations.AddField(
            model_name='category',
            name='sale',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='shop.Sale', verbose_name='Sale'),
        ),
        migrations.AlterUniqueTogether(
            name='productaction',
            unique_together=set([('product', 'timestamp')]),
        ),
        migrations.AlterUniqueTogether(
            name='product',
            unique_together=set([('sku', 'site')]),
        ),
    ]
