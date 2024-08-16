from rest_framework import generics
from .models_test import *
from .serializers_test import *

# Test views used by unauthenticated users test applications, like a portfolio.

class CustomerTestListView(generics.ListAPIView):
    queryset = CustomerTest.objects.all()
    serializer_class = CustomerTestSerializer


class CustomerTestCreateView(generics.ListCreateAPIView):
    queryset = CustomerTest.objects.all()
    serializer_class = CustomerTestSerializer


class CustomerTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomerTest.objects.all()
    serializer_class = CustomerTestSerializer

class ExpenseTestListView(generics.ListAPIView):
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer


class ExpenseTestCreateView(generics.ListCreateAPIView):
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer


class ExpenseTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer


class RevenueTestListView(generics.ListAPIView):
    queryset = RevenueTest.objects.all()
    serializer_class = RevenueTestSerializer


class RevenueTestCreateView(generics.ListCreateAPIView):
    queryset = RevenueTest.objects.all()
    serializer_class = RevenueTestSerializer


class RevenueTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RevenueTest.objects.all()
    serializer_class = RevenueTestSerializer

