from rest_framework import generics
from datetime import timedelta
from django.utils import timezone
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from dental_clinic.utils import createInstallments, perform_calculations, gross_profit_of_the_last_12_months
from rest_framework.exceptions import ValidationError
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
    Lists monthly cash closings.
    '''
    permission_classes = [IsAuthenticated]
    queryset = MonthClosing.objects.all()
    serializer_class = MonthClosingSerializer

    def get_queryset(self):
        """
        Returns the monthly closings for the year specified in the query param 'year'.
        """
        year = self.request.query_params.get('year')

        if not year:
            raise ValidationError({"detail": "O parâmetro 'ano' é obrigatório."})

        try:
            year = int(year)
        except ValueError:
            raise ValidationError({"detail": "O parâmetro 'ano' deve ser um número inteiro."})

        return MonthClosing.objects.filter(year=year).order_by('month')


class MonthClosingCreateUpdateView(generics.ListCreateAPIView, generics.RetrieveUpdateDestroyAPIView):
    '''
    Creates and updates monthly cash closing data.
    '''
    permission_classes = [IsAuthenticated]
    queryset = MonthClosing.objects.all()
    serializer_class = MonthClosingSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        data = perform_calculations(Revenue, Expense, data)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data

        data = perform_calculations(Revenue, Expense, data)

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Block the deletion of monthly cash closings.
        """
        return Response({'detail': 'A exclusão de fechamentos mensais de caixa não é permitida.'}, status=status.HTTP_403_FORBIDDEN)


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


class ProfitListView(APIView):
    """
    Returns a list of monthly gross profits for the last 12 months.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profit_data, labels = gross_profit_of_the_last_12_months(Revenue, Expense)

        return Response({"profit": profit_data, "labels": labels})
    

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
    Lists monthly cash closings.
    '''
    permission_classes = [AllowAny]
    queryset = MonthClosingTest.objects.all()
    serializer_class = MonthClosingTestSerializer

    def get_queryset(self):
        """
        Returns the monthly closings for the year specified in the query param 'year'.
        """
        year = self.request.query_params.get('year')

        if not year:
            raise ValidationError({"detail": "O parâmetro 'ano' é obrigatório."})

        try:
            year = int(year)
        except ValueError:
            raise ValidationError({"detail": "O parâmetro 'ano' deve ser um número inteiro."})

        return MonthClosingTest.objects.filter(year=year).order_by('month')


class MonthClosingTestCreateUpdateView(generics.ListCreateAPIView, generics.RetrieveUpdateDestroyAPIView):
    '''
    Creates and updates monthly cash closing data.
    '''
    permission_classes = [AllowAny]
    queryset = MonthClosingTest.objects.all()
    serializer_class = MonthClosingTestSerializer

    def create(self, request, *args, **kwargs):
        '''
        Creates the cash closing for a specific month.
        '''
        data = request.data
        data = perform_calculations(RevenueTest, ExpenseTest, data)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        '''
        Updates the cash closing for a specific month.
        '''
        instance = self.get_object()
        data = request.data

        data = perform_calculations(RevenueTest, ExpenseTest, data)

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Block the deletion of monthly cash closings.
        """
        return Response({'detail': 'A exclusão de fechamentos mensais de caixa não é permitida.'}, status=status.HTTP_403_FORBIDDEN)

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
    

class ProfitTestListView(APIView):
    """
    Returns a list of monthly gross profits for the last 12 months.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        profit_data, labels = gross_profit_of_the_last_12_months(RevenueTest, ExpenseTest)

        return Response({"profit": profit_data, "labels": labels})
