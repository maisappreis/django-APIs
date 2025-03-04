from rest_framework import generics
from datetime import timedelta
from django.utils import timezone
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
    """
    List revenues.
    """
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer

    def get_queryset(self):
        """
        Lists all revenue from the last 12 months.
        """
        twelve_months_ago = timezone.now() - timedelta(days=370)
        return Revenue.objects.filter(date__gte=twelve_months_ago).order_by('-date')


class RevenueCreateView(generics.ListCreateAPIView):
    """
    Create a revenue.
    """
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class RevenueUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Update and delete a revenue.
    """
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class ExpenseListView(generics.ListAPIView):
    """
    Lists expenses.
    """
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        """
        Lists all expenses from the last 12 months.
        """
        twelve_months_ago = timezone.now() - timedelta(days=370)
        return Expense.objects.filter(date__gte=twelve_months_ago).order_by('-date')


class ExpenseCreateView(generics.ListCreateAPIView):
    """
    Create a expense.
    """
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
    """
    Update and delete a expense.
    """
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class AgendaListView(generics.ListAPIView):
    '''
    List appointments.
    '''
    permission_classes = [IsAuthenticated]
    queryset = Agenda.objects.all()
    serializer_class = AgendaSerializer


class AgendaCreateView(generics.ListCreateAPIView):
    '''
    Create a appointment.
    '''
    permission_classes = [IsAuthenticated]
    queryset = Agenda.objects.all()
    serializer_class = AgendaSerializer


class AgendaUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    '''
    Update and delete a appointment.
    '''
    permission_classes = [IsAuthenticated]
    queryset = Agenda.objects.all()
    serializer_class = AgendaSerializer


class MonthClosingListView(generics.ListAPIView):
    '''
    Lists all the data required for the monthly cash closing.
    '''
    permission_classes = [IsAuthenticated]
    queryset = MonthClosing.objects.all()
    serializer_class = MonthClosingSerializer


class MonthClosingCreateUpdateView(generics.ListCreateAPIView, generics.RetrieveUpdateDestroyAPIView):
    '''
    Creates and updates monthly cash closing data.
    '''
    permission_classes = [IsAuthenticated]
    queryset = MonthClosing.objects.all()
    serializer_class = MonthClosingSerializer

    def perform_calculations(self, data):
        month = data.get('month')
        year = data.get('year')
        bank_value = data.get('bank_value')
        cash_value = data.get('cash_value')
        card_value = data.get('card_value')
        card_value_next_month = data.get('card_value_next_month')
        expenses = data.get('expenses')
        other_revenue = data.get('other_revenue')

        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        gross_revenue = calculate_sum_values(Revenue, month=month, year=year, date_field='date')
        net_revenue = calculate_sum_values(Revenue, month=month, year=year, date_field='date', value_field='net_value')
        expenses = calculate_sum_values(Expense, month=next_month, year=next_year)

        half_expenses = expenses/2
        profit = calculate_profit(net_revenue, half_expenses)
        
        card_value_this_month = card_value - card_value_next_month
        balance = calculate_balance(bank_value, cash_value, card_value_this_month, other_revenue, expenses, profit)

        data['bank_value'] = bank_value
        data['cash_value'] = cash_value
        data['card_value'] = card_value
        data['card_value_next_month'] = card_value_next_month
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

    # TODO: bloquear o destroy aqui.

class UpdateNetValuesView(APIView):
    '''
    Updates net revenue values.
    '''
    permission_classes = [IsAuthenticated]
    
    def put(self, request, *args, **kwargs):
        serializer = RevenueNetValueUpdateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            for item in serializer.validated_data:
                try:
                    revenue = Revenue.objects.get(id=item['id'])
                    revenue.net_value = item['net_value']
                    revenue.date = item['date']
                    revenue.save()
                except Revenue.DoesNotExist:
                    return Response({"detail": f"Revenue with id {item['id']} not found."}, status=status.HTTP_404_NOT_FOUND)

            return Response({"detail": "Net values updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# Test views used by unauthenticated users test application, like a portfolio.


class RevenueTestListView(generics.ListAPIView):
    """
    List revenues.
    """
    permission_classes = [AllowAny]
    queryset = RevenueTest.objects.all()
    serializer_class = RevenueTestSerializer

    def get_queryset(self):
        """
        Lists all revenue from the last 12 months.
        """
        twelve_months_ago = timezone.now() - timedelta(days=370)
        return RevenueTest.objects.filter(date__gte=twelve_months_ago).order_by('-date')


class RevenueTestCreateView(generics.ListCreateAPIView):
    """
    Create a revenue.
    """
    permission_classes = [AllowAny]
    queryset = RevenueTest.objects.all()
    serializer_class = RevenueTestSerializer


class RevenueTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Update and delete a revenue.
    """
    permission_classes = [AllowAny]
    queryset = RevenueTest.objects.all()
    serializer_class = RevenueTestSerializer


class ExpenseTestListView(generics.ListAPIView):
    """
    Lists expenses.
    """
    permission_classes = [AllowAny]
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer

    def get_queryset(self):
        """
        Lists all expenses from the last 12 months.
        """
        twelve_months_ago = timezone.now() - timedelta(days=370)
        return ExpenseTest.objects.filter(date__gte=twelve_months_ago).order_by('-date')


class ExpenseTestCreateView(generics.ListCreateAPIView):
    """
    Create a expense.
    """
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
    """
    Update and delete a expense.
    """
    permission_classes = [AllowAny]
    queryset = ExpenseTest.objects.all()
    serializer_class = ExpenseTestSerializer


class AgendaTestListView(generics.ListAPIView):
    '''
    List appointments.
    '''
    permission_classes = [AllowAny]
    queryset = AgendaTest.objects.all()
    serializer_class = AgendaTestSerializer


class AgendaTestCreateView(generics.ListCreateAPIView):
    '''
    Create a appointment.
    '''
    permission_classes = [AllowAny]
    queryset = AgendaTest.objects.all()
    serializer_class = AgendaTestSerializer


class AgendaTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    '''
    Update and delete a appointment.
    '''
    permission_classes = [AllowAny]
    queryset = AgendaTest.objects.all()
    serializer_class = AgendaTestSerializer


class MonthClosingTestListView(generics.ListAPIView):
    '''
    Lists all the data required for the monthly cash closing.
    '''
    permission_classes = [AllowAny]
    queryset = MonthClosingTest.objects.all()
    serializer_class = MonthClosingTestSerializer


class MonthClosingTestCreateUpdateView(generics.ListCreateAPIView, generics.RetrieveUpdateDestroyAPIView):
    '''
    Creates and updates monthly cash closing data.
    '''
    permission_classes = [AllowAny]
    queryset = MonthClosingTest.objects.all()
    serializer_class = MonthClosingTestSerializer

    def perform_calculations(self, data):
        month = data.get('month')
        year = data.get('year')
        bank_value = data.get('bank_value')
        cash_value = data.get('cash_value')
        card_value = data.get('card_value')
        card_value_next_month = data.get('card_value_next_month')
        expenses = data.get('expenses')
        other_revenue = data.get('other_revenue')

        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        gross_revenue = calculate_sum_values(RevenueTest, month=month, year=year, date_field='date')
        net_revenue = calculate_sum_values(RevenueTest, month=month, year=year, date_field='date', value_field='net_value')
        expenses = calculate_sum_values(ExpenseTest, month=next_month, year=next_year)
        
        half_expenses = expenses/2
        profit = calculate_profit(net_revenue, half_expenses)
        
        card_value_this_month = card_value - card_value_next_month
        balance = calculate_balance(bank_value, cash_value, card_value_this_month, other_revenue, expenses, profit)

        data['bank_value'] = bank_value
        data['cash_value'] = cash_value
        data['card_value'] = card_value
        data['card_value_next_month'] = card_value_next_month
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

    # TODO: bloquear o destroy aqui.

class UpdateNetValuesTestView(APIView):
    '''
    Updates net revenue values.
    '''
    permission_classes = [AllowAny]
    
    def put(self, request, *args, **kwargs):
        serializer = RevenueTestNetValueUpdateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            for item in serializer.validated_data:
                try:
                    revenue = RevenueTest.objects.get(id=item['id'])
                    revenue.net_value = item['net_value']
                    revenue.date = item['date']
                    revenue.save()
                except Revenue.DoesNotExist:
                    return Response({"detail": f"Revenue with id {item['id']} not found."}, status=status.HTTP_404_NOT_FOUND)

            return Response({"detail": "Net values updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)