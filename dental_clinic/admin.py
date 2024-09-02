from django.contrib import admin
from .models import *


@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'cpf', 'procedure', 'payment', 'installments', 'value', 'notes')
    search_fields = ('name', 'cpf')
    list_filter = ('date', 'name', 'cpf')
    ordering = ('date',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'month', 'installments', 'date', 'value', 'is_paid', 'notes')
    search_fields = ('name', 'date')
    list_filter = ('name', 'year', 'month', 'date')
    ordering = ('date',)


@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'time', 'notes')
    search_fields = ('name', 'date')
    list_filter = ('name', 'date', 'time')
    ordering = ('date',)


@admin.register(RevenueTest)
class RevenueTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'cpf', 'procedure', 'payment', 'installments', 'value', 'notes')
    search_fields = ('name', 'cpf')
    list_filter = ('date', 'name', 'cpf')
    ordering = ('date',)


@admin.register(ExpenseTest)
class ExpenseTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'month', 'installments', 'date', 'value', 'is_paid', 'notes')
    search_fields = ('name', 'date')
    list_filter = ('name', 'year', 'month', 'date')
    ordering = ('date',)


@admin.register(AgendaTest)
class AgendaTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'time', 'notes')
    search_fields = ('name', 'date')
    list_filter = ('name', 'date', 'time')
    ordering = ('date',)
