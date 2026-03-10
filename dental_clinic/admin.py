from django.contrib import admin
from .models import *


@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'release_date', 'name', 'cpf', 'procedure', 'payment', 'installments', 'value', 'net_value', 'notes')
    search_fields = ('name', 'cpf')
    list_filter = ('date', 'name', 'cpf')
    ordering = ('date',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'year', 'month', 'installments', 'date', 'value', 'is_paid', 'notes')
    search_fields = ('name', 'date')
    list_filter = ('name', 'year', 'month', 'date')
    ordering = ('date',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'date', 'time', 'notes')
    search_fields = ('name', 'date')
    list_filter = ('name', 'date', 'time')
    ordering = ('date',)


@admin.register(MonthClosing)
class MonthClosingAdmin(admin.ModelAdmin):
    list_display = ('user', 'reference', 'month', 'year', 'bank_value', 'cash_value', 'card_value', 'card_value_next_month', 'gross_revenue', 'net_revenue', 'expenses', 'net_profit', 'other_revenue', 'balance')
    search_fields = ('reference', 'month', 'year')
    list_filter = ('reference', 'month', 'year')
    ordering = ('reference',)