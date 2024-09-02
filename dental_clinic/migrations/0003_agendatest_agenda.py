# Generated by Django 4.2.9 on 2024-09-02 10:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dental_clinic', '0002_revenue_expense'),
    ]

    operations = [
        migrations.CreateModel(
            name='AgendaTest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('date', models.DateField()),
                ('time', models.CharField(max_length=10)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'unique_together': {('name', 'date', 'time')},
            },
        ),
        migrations.CreateModel(
            name='Agenda',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('date', models.DateField()),
                ('time', models.CharField(max_length=10)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'unique_together': {('name', 'date', 'time')},
            },
        ),
    ]
