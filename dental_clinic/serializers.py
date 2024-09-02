from rest_framework import serializers
from .models import *

# Real serializers used by authenticated users.


class RevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revenue
        fields = '__all__'


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'


class AgendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agenda
        fields = '__all__'


# Test serializers used by unauthenticated users test application, like a portfolio.


class RevenueTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueTest
        fields = '__all__'


class ExpenseTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseTest
        fields = '__all__'


class AgendaTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgendaTest
        fields = '__all__'