from rest_framework import serializers
from .models import *

# Real serializers used by authenticated users.


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class RevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revenue
        fields = '__all__'


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'


# Test serializers used by unauthenticated users test application, like a portfolio.


class CustomerTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerTest
        fields = '__all__'


class RevenueTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueTest
        fields = '__all__'


class ExpenseTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseTest
        fields = '__all__'
