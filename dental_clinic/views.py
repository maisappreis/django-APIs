from datetime import timedelta
from django.utils import timezone

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import generics

from dental_clinic.services.month_closing import MonthClosingService
from dental_clinic.services.dashboard import DashboardService
from dental_clinic.services.revenue import RevenueService
from dental_clinic.services.expense import ExpenseService
from dental_clinic.serializers import *
from dental_clinic.models import *
from dental_clinic.mixins import *


class RevenueListView(UserQuerySetMixin, generics.ListAPIView):
    '''
    List revenues.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = RevenueSerializer
    queryset = Revenue.objects.all()

    def get_queryset(self):
        '''
        Lists all revenue from the last 12 months.
        '''
        twelve_months_ago = timezone.now() - timedelta(days=370)

        return super().get_queryset().filter(
            date__gte=twelve_months_ago
        ).order_by('-date')


class RevenueCreateView(UserQuerySetMixin, UserCreateMixin, generics.CreateAPIView):
    '''
    Create a revenue.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = RevenueSerializer
    queryset = Revenue.objects.all()


class RevenueUpdateDestroyView(UserQuerySetMixin, generics.RetrieveUpdateDestroyAPIView):
    '''
    Update and delete a revenue.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = RevenueSerializer
    queryset = Revenue.objects.all()


class ExpenseListView(UserQuerySetMixin, generics.ListAPIView):
    '''
    Lists expenses.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()

    def get_queryset(self):
        '''
        Lists all expenses from the last 12 months.
        '''
        twelve_months_ago = timezone.now() - timedelta(days=370)

        return super().get_queryset().filter(
            date__gte=twelve_months_ago
        ).order_by('-date')


class ExpenseCreateView(generics.CreateAPIView):
    '''
    Create a expense.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        expenses = ExpenseService.create_expenses(
            user=request.user,
            validated_data=serializer.validated_data
        )

        return Response(
            ExpenseSerializer(expenses, many=True).data,
            status=status.HTTP_201_CREATED
        )


class ExpenseUpdateDestroyView(UserQuerySetMixin, generics.RetrieveUpdateDestroyAPIView):
    '''
    Update and delete a expense.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()


class AppointmentListView(UserQuerySetMixin, generics.ListAPIView):
    '''
    List appointments.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer
    queryset = Appointment.objects.all()


class AppointmentCreateView(UserQuerySetMixin, UserCreateMixin, generics.CreateAPIView):
    '''
    Create a appointment.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer
    queryset = Appointment.objects.all()


class AppointmentUpdateDestroyView(UserQuerySetMixin, generics.RetrieveUpdateDestroyAPIView):
    '''
    Update and delete a appointment.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer
    queryset = Appointment.objects.all()


class MonthClosingListView(generics.ListAPIView):
    '''
    Lists monthly cash closings.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = MonthClosingSerializer

    def get_queryset(self):
        '''
        Returns the monthly closings for the year specified in the query param 'year'.
        '''
        year = self.request.query_params.get('year')

        if not year:
            raise ValidationError({'detail': 'O parâmetro "ano" é obrigatório.'})

        try:
            year = int(year)
        except ValueError:
            raise ValidationError({'detail': 'O parâmetro "ano" deve ser um número inteiro.'})

        return MonthClosing.objects.filter(
            user=self.request.user,
            year=year
        ).order_by('month')
    

class MonthClosingCreateView(UserCreateMixin, generics.CreateAPIView):
    '''
    Create a monthly cash closings.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = MonthClosingSerializer
    queryset = MonthClosing.objects.all()

    def create(self, request, *args, **kwargs):

        data = MonthClosingService.calculate(
            request.user,
            request.data
        )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MonthClosingUpdateDestroyView(UserQuerySetMixin, generics.RetrieveUpdateDestroyAPIView):
    '''
    Update and delete a monthly cash closings.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = MonthClosingSerializer
    queryset = MonthClosing.objects.all()

    def update(self, request, *args, **kwargs):

        instance = self.get_object()

        data = MonthClosingService.calculate(
            request.user,
            request.data
        )

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        return Response(serializer.data)


class UpdateNetValuesView(APIView):
    '''
    Update net values on Revenue.
    That is, after debit and credit card fees have been deducted.
    '''
    permission_classes = [IsAuthenticated]

    def put(self, request):

        serializer = RevenueNetValueUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reference = serializer.validated_data['reference']
        revenue_items = serializer.validated_data['revenue']

        try:

            month_closing = RevenueService.update_net_values(
                user=request.user,
                revenue_items=revenue_items,
                reference=reference
            )

        except ValueError as e:

            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                'detail': 'Net values updated successfully.',
                'month_closing': MonthClosingSerializer(month_closing).data
            }
        )


class DashboardChartsView(APIView):
    '''
    Returns chart data for the dashboard (last 12 months).
    '''

    permission_classes = [IsAuthenticated]

    def get(self, request):

        data = DashboardService.get_charts(request.user)

        return Response(data)
