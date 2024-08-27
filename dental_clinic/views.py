from rest_framework import generics
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime
from dateutil.relativedelta import relativedelta
import locale

# Real views used by authenticated users.


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


class ExpenseListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class ExpenseCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    def create(self, request, *args, **kwargs):
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        
        data = request.data
        installments = data.get('installments', "")

        if installments == "":
            return super().create(request, *args, **kwargs)

        installments = int(installments)
        initial_date = datetime.strptime(data['date'], "%Y-%m-%d")
        created_objects = []

        for i in range(installments):
            installment_data = data.copy()
            installment_data['installments'] = f"{i+1}/{installments}"
            installment_data['date'] = (initial_date + relativedelta(months=i)).strftime("%Y-%m-%d")
            month = (initial_date + relativedelta(months=i)).strftime("%B").capitalize()
            installment_data['month'] = month
            installment_data['year'] = (initial_date + relativedelta(months=i)).year

            serializer = self.get_serializer(data=installment_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            created_objects.append(serializer.data)

        headers = self.get_success_headers(serializer.data)
        return Response(created_objects, status=201, headers=headers)


class ExpenseUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


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
    
    def create(self, request, *args, **kwargs):
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        
        data = request.data
        installments = data.get('installments', "")

        if installments == "":
            return super().create(request, *args, **kwargs)
        
        installments = int(installments)
        initial_date = datetime.strptime(data['date'], "%Y-%m-%d")
        created_objects = []

        for i in range(installments):
            installment_data = data.copy()
            installment_data['installments'] = f"{i+1}/{installments}"
            installment_data['date'] = (initial_date + relativedelta(months=i)).strftime("%Y-%m-%d")
            month = (initial_date + relativedelta(months=i)).strftime("%B").capitalize()
            installment_data['month'] = month
            installment_data['year'] = (initial_date + relativedelta(months=i)).year

            serializer = self.get_serializer(data=installment_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            created_objects.append(serializer.data)

        headers = self.get_success_headers(serializer.data)
        return Response(created_objects, status=201, headers=headers)


class ExpenseTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer