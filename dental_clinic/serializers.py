from rest_framework import serializers
from .models import *


class RevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revenue
        fields = '__all__'
        read_only_fields = ["user"]


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ["user"]


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ["user"]


class MonthClosingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthClosing
        fields = '__all__'
        read_only_fields = ["user"]


class RevenueNetValueItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    net_value = serializers.FloatField()
    date = serializers.DateField()


class RevenueNetValueUpdateSerializer(serializers.Serializer):
    reference = serializers.CharField()
    revenue = RevenueNetValueItemSerializer(many=True)