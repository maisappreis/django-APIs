from rest_framework import generics
from .models import *
from .serializers import *

# Real views used by authenticated users.


from rest_framework.permissions import IsAuthenticated

class CustomerListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class ExpenseListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class ExpenseCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class ExpenseUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class RevenueListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class RevenueCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class RevenueUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer

