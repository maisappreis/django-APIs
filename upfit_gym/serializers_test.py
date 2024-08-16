from rest_framework import serializers
from .models_test import *

# Test serializers used by unauthenticated users test applications, like a portfolio.


class CustomerTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerTest
        fields = '__all__'


class ExpenseTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseTest
        fields = '__all__'


class RevenueTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueTest
        fields = '__all__'