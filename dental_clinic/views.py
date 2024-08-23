from rest_framework import generics
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated

# Real views used by authenticated users.


# class RevenueListView(generics.ListAPIView):
#     permission_classes = [IsAuthenticated]
#     queryset = Revenue.objects.all()
#     serializer_class = RevenueSerializer


# class RevenueCreateView(generics.ListCreateAPIView):
#     permission_classes = [IsAuthenticated]
#     queryset = Revenue.objects.all()
#     serializer_class = RevenueSerializer


# class RevenueUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
#     permission_classes = [IsAuthenticated]
#     queryset = Revenue.objects.all()
#     serializer_class = RevenueSerializer


# class ExpenseListView(generics.ListAPIView):
#     permission_classes = [IsAuthenticated]
#     queryset = Expense.objects.all()
#     serializer_class = ExpenseSerializer


# class ExpenseCreateView(generics.ListCreateAPIView):
#     permission_classes = [IsAuthenticated]
#     queryset = Expense.objects.all()
#     serializer_class = ExpenseSerializer


# class ExpenseUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
#     permission_classes = [IsAuthenticated]
#     queryset = Expense.objects.all()
#     serializer_class = ExpenseSerializer


# Test views used by unauthenticated users test application, like a portfolio.


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


class ExpenseTestListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer


class ExpenseTestCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer
    # TODO: Sobre o installments:
    # O front para para o back uma requisição de post com installments: "6"
    # O back transforma a string "6" em número, e cria 6 objetos recorrentes, pelos 6 meses seguintes.
    # Para salvar no banco, ele salva "1 / 6", "2/6", "3/6",.... até "6/6" como string.


class ExpenseTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer