# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-22 17:28
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import invites.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('invites', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvitationCode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(blank=True, default=django.utils.timezone.now, editable=False)),
                ('registered_to', models.EmailField(max_length=254, verbose_name='email')),
                ('registered_name', models.CharField(blank=True, max_length=70, null=True, verbose_name='name')),
                ('key', models.CharField(blank=True, editable=False, max_length=30, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=invites.models.get_default_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('site', models.ForeignKey(default=invites.models.get_default_site, on_delete=django.db.models.deletion.CASCADE, related_name='invite_codes', to='sites.Site')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='invitationcode',
            unique_together=set([('site', 'key')]),
        ),
    ]
