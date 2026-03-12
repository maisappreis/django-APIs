from django.contrib import admin
from .models import *


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'frequency', 'start', 'plan', 'value', 'status')
    search_fields = ('name', 'plan')
    list_filter = ('status', 'frequency')
    ordering = ('name',)


@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ('user', 'customer', 'year', 'month', 'payment_day', 'value', 'paid')
    search_fields = ('customer__name',)
    list_filter = ('paid', 'year', 'month', 'customer')
    ordering = ('customer', 'year', 'month')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'year', 'month', 'date', 'value', 'paid')
    search_fields = ('name',)
    list_filter = ('paid', 'year', 'month')
    ordering = ('year', 'month')