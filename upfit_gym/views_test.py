from rest_framework import generics
from .models_test import *
from .serializers_test import *
from rest_framework.permissions import AllowAny

# Test views used by unauthenticated users test applications, like a portfolio.

class CustomerTestListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = CustomerTest.objects.all()
    serializer_class = CustomerTestSerializer


class CustomerTestCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    queryset = CustomerTest.objects.all()
    serializer_class = CustomerTestSerializer


class CustomerTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = CustomerTest.objects.all()
    serializer_class = CustomerTestSerializer


class ExpenseTestListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer


class ExpenseTestCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer


class ExpenseTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer


class RevenueTestListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = RevenueTest.objects.all()
    serializer_class = RevenueTestSerializer


class RevenueTestCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    queryset = RevenueTest.objects.all()
    serializer_class = RevenueTestSerializer


class RevenueTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = RevenueTest.objects.all()
    serializer_class = RevenueTestSerializer

