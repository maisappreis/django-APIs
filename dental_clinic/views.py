from rest_framework import generics
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from dental_clinic.utils import createInstallments
from rest_framework.views import APIView
from rest_framework import status
from .utils import *

# Real views used by authenticated users.


class RevenueListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer

    # def get_queryset(self):
    #     return Revenue.objects.filter(user=self.request.user)


class RevenueCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer

    # def get_queryset(self):
    #     return Revenue.objects.filter(user=self.request.user)

    # def perform_create(self, serializer):
    #     serializer.save(user=self.request.user)


class RevenueUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer

    # def get_queryset(self):
    #     return Revenue.objects.filter(user=self.request.user)


class ExpenseListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class ExpenseCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        installments = data.get('installments', "")

        if installments == "":
            return super().create(request, *args, **kwargs)
        
        serializer, created_objects = createInstallments(
            serializer_class=self.get_serializer_class(),
            perform_create=self.perform_create,
            installments=installments,
            data=data
        )

        headers = self.get_success_headers(serializer.data)
        return Response(created_objects, status=201, headers=headers)


class ExpenseUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class AgendaListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Agenda.objects.all()
    serializer_class = AgendaSerializer


class AgendaCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Agenda.objects.all()
    serializer_class = AgendaSerializer


class AgendaUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Agenda.objects.all()
    serializer_class = AgendaSerializer


class MonthClosingListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = MonthClosing.objects.all()
    serializer_class = MonthClosingSerializer


class MonthClosingCreateUpdateView(generics.ListCreateAPIView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = MonthClosing.objects.all()
    serializer_class = MonthClosingSerializer

    def perform_calculations(self, data):
        month = data.get('month')
        year = data.get('year')
        bank_value = data.get('bank_value')
        cash_value = data.get('cash_value')
        card_value = data.get('card_value')
        expenses = data.get('expenses')
        other_revenue = data.get('other_revenue')

        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        gross_revenue = calculate_sum_values(Revenue, month=month, year=year)
        net_revenue = calculate_sum_values(Revenue, month=month, year=year, value_field='net_value')
        expenses = calculate_sum_values(Expense, month=next_month, year=next_year)
        profit = calculate_profit(net_revenue, expenses)
        balance = calculate_balance(bank_value, cash_value, card_value, other_revenue, expenses, profit)

        data['bank_value'] = bank_value
        data['cash_value'] = cash_value
        data['card_value'] = card_value
        data['gross_revenue'] = gross_revenue
        data['net_revenue'] = net_revenue
        data['expenses'] = expenses
        data['profit'] = profit
        data['other_revenue'] = expenses/2
        data['balance'] = balance

        return data

    def create(self, request, *args, **kwargs):
        data = request.data
        data = self.perform_calculations(data)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data

        data = self.perform_calculations(data)

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateNetValuesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request, *args, **kwargs):
        serializer = RevenueNetValueUpdateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            for item in serializer.validated_data:
                try:
                    revenue = Revenue.objects.get(id=item['id'])
                    revenue.net_value = item['net_value']
                    revenue.save()
                except Revenue.DoesNotExist:
                    return Response({"detail": f"Revenue with id {item['id']} not found."}, status=status.HTTP_404_NOT_FOUND)

            return Response({"detail": "Net values updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

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
        data = request.data
        installments = data.get('installments', "")

        if installments == "":
            return super().create(request, *args, **kwargs)
        
        serializer, created_objects = createInstallments(
            serializer_class=self.get_serializer_class(),
            perform_create=self.perform_create,
            installments=installments,
            data=data
        )

        headers = self.get_success_headers(serializer.data)
        return Response(created_objects, status=201, headers=headers)


class ExpenseTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer


class AgendaTestListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = AgendaTest.objects.all()
    serializer_class = AgendaTestSerializer


class AgendaTestCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    queryset = AgendaTest.objects.all()
    serializer_class = AgendaTestSerializer


class AgendaTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = AgendaTest.objects.all()
    serializer_class = AgendaTestSerializer


class MonthClosingTestListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = MonthClosingTest.objects.all()
    serializer_class = MonthClosingTestSerializer


class MonthClosingTestCreateUpdateView(generics.ListCreateAPIView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = MonthClosingTest.objects.all()
    serializer_class = MonthClosingTestSerializer

    def perform_calculations(self, data):
        month = data.get('month')
        year = data.get('year')
        bank_value = data.get('bank_value')
        cash_value = data.get('cash_value')
        card_value = data.get('card_value')
        expenses = data.get('expenses')
        other_revenue = data.get('other_revenue')

        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        gross_revenue = calculate_sum_values(RevenueTest, month=month, year=year)
        net_revenue = calculate_sum_values(RevenueTest, month=month, year=year, value_field='net_value')
        expenses = calculate_sum_values(ExpenseTest, month=next_month, year=next_year)
        profit = calculate_profit(net_revenue, expenses)
        balance = calculate_balance(bank_value, cash_value, card_value, other_revenue, expenses, profit)

        data['bank_value'] = bank_value
        data['cash_value'] = cash_value
        data['card_value'] = card_value
        data['gross_revenue'] = gross_revenue
        data['net_revenue'] = net_revenue
        data['expenses'] = expenses
        data['profit'] = profit
        data['other_revenue'] = expenses/2
        data['balance'] = balance

        return data

    def create(self, request, *args, **kwargs):
        data = request.data
        data = self.perform_calculations(data)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data

        data = self.perform_calculations(data)

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateNetValuesTestView(APIView):
    permission_classes = [AllowAny]
    
    def put(self, request, *args, **kwargs):
        serializer = RevenueTestNetValueUpdateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            for item in serializer.validated_data:
                try:
                    revenue = RevenueTest.objects.get(id=item['id'])
                    revenue.net_value = item['net_value']
                    revenue.save()
                except Revenue.DoesNotExist:
                    return Response({"detail": f"Revenue with id {item['id']} not found."}, status=status.HTTP_404_NOT_FOUND)

            return Response({"detail": "Net values updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)