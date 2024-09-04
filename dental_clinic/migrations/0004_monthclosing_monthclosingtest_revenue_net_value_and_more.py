# Generated by Django 4.2.9 on 2024-09-03 12:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dental_clinic', '0003_agendatest_agenda'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonthClosing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(max_length=55, unique=True)),
                ('month', models.IntegerField()),
                ('year', models.IntegerField()),
                ('bank_value', models.FloatField()),
                ('cash_value', models.FloatField()),
                ('card_value', models.FloatField()),
                ('gross_revenue', models.FloatField()),
                ('net_revenue', models.FloatField()),
                ('expenses', models.FloatField()),
                ('profit', models.FloatField()),
                ('other_revenue', models.FloatField()),
                ('balance', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='MonthClosingTest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(max_length=55, unique=True)),
                ('month', models.IntegerField()),
                ('year', models.IntegerField()),
                ('bank_value', models.FloatField()),
                ('cash_value', models.FloatField()),
                ('card_value', models.FloatField()),
                ('gross_revenue', models.FloatField()),
                ('net_revenue', models.FloatField()),
                ('expenses', models.FloatField()),
                ('profit', models.FloatField()),
                ('other_revenue', models.FloatField()),
                ('balance', models.FloatField()),
            ],
        ),
        migrations.AddField(
            model_name='revenue',
            name='net_value',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='revenuetest',
            name='net_value',
            field=models.FloatField(default=0),
        ),
    ]
