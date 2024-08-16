from django.contrib import admin
from .models import Customer, Expense, Revenue
from .models_test import CustomerTest, ExpenseTest, RevenueTest


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'frequency', 'start', 'plan', 'value', 'status')
    search_fields = ('name', 'plan')
    list_filter = ('status', 'frequency')
    ordering = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'month', 'due_date', 'value', 'paid')
    search_fields = ('name',)
    list_filter = ('paid', 'year', 'month')
    ordering = ('year', 'month')


@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ('customer', 'year', 'month', 'payment_day', 'value', 'paid')
    search_fields = ('customer__name',)
    list_filter = ('paid', 'year', 'month', 'customer')
    ordering = ('customer', 'year', 'month')


@admin.register(CustomerTest)
class CustomerTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'frequency', 'start', 'plan', 'value', 'status')
    search_fields = ('name', 'plan')
    list_filter = ('status', 'frequency')
    ordering = ('name',)


@admin.register(ExpenseTest)
class ExpenseTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'month', 'due_date', 'value', 'paid')
    search_fields = ('name',)
    list_filter = ('paid', 'year', 'month')
    ordering = ('year', 'month')


@admin.register(RevenueTest)
class RevenueTestAdmin(admin.ModelAdmin):
    list_display = ('customer', 'year', 'month', 'payment_day', 'value', 'paid')
    search_fields = ('customer__name',)
    list_filter = ('paid', 'year', 'month', 'customer')
    ordering = ('customer', 'year', 'month')