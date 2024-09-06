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


class MonthClosingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthClosing
        fields = '__all__'


class RevenueNetValueUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    net_value = serializers.FloatField()
    release_date = serializers.DateField()

    class Meta:
        model = Revenue
        fields = ['id', 'net_value', 'release_date']


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


class MonthClosingTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthClosingTest
        fields = '__all__'


class RevenueTestNetValueUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    net_value = serializers.FloatField()
    release_date = serializers.DateField()

    class Meta:
        model = RevenueTest
        fields = ['id', 'net_value', 'release_date']