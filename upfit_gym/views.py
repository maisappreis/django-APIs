from rest_framework import generics
from .models import *
from .serializers import *
# from rest_framework.authentication import TokenAuthentication

# Real views used by authenticated users.


from rest_framework.permissions import IsAuthenticated

class CustomerListView(generics.ListAPIView):
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerCreateView(generics.ListCreateAPIView):
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class ExpenseListView(generics.ListAPIView):
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class ExpenseCreateView(generics.ListCreateAPIView):
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class ExpenseUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class RevenueListView(generics.ListAPIView):
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class RevenueCreateView(generics.ListCreateAPIView):
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class RevenueUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer

