# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
from rest_framework import generics
from .models import *
from .serializers import *


class CustomerListView(generics.ListAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


# class CustomerListView(APIView):

#     def get(self, request, *args, **kwargs):
#         customers = Customer.objects.all()
#         serializer = CustomerSerializer(customers, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)


class ExpenseListView(generics.ListAPIView):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class ExpenseCreateView(generics.ListCreateAPIView):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class ExpenseUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class RevenueListView(generics.ListAPIView):
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class RevenueCreateView(generics.ListCreateAPIView):
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class RevenueUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer

