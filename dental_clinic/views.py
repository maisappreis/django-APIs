from datetime import timedelta
from django.utils import timezone
from django.db import transaction

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import generics

from dental_clinic.service import ExpenseService
from dental_clinic.serializers import *
from dental_clinic.models import *
from dental_clinic.utils import *


class RevenueListView(generics.ListAPIView):
    """
    List revenues.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RevenueSerializer

    def get_queryset(self):
        """
        Lists all revenue from the last 12 months.
        """
        twelve_months_ago = timezone.now() - timedelta(days=370)

        return Revenue.objects.filter(
            user=self.request.user,
            date__gte=twelve_months_ago
        ).order_by('-date')


class RevenueCreateView(generics.ListCreateAPIView):
    """
    Create a revenue.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RevenueSerializer

    def get_queryset(self):
        return Revenue.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RevenueUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Update and delete a revenue.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RevenueSerializer

    def get_queryset(self):
        return Revenue.objects.filter(user=self.request.user)


class ExpenseListView(generics.ListAPIView):
    """
    Lists expenses.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        """
        Lists all expenses from the last 12 months.
        """
        twelve_months_ago = timezone.now() - timedelta(days=370)

        return Expense.objects.filter(
            user=self.request.user,
            date__gte=twelve_months_ago
        ).order_by('-date')


class ExpenseCreateView(generics.ListCreateAPIView):
    """
    Create a expense.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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


class ExpenseUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Update and delete a expense.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)


class AppointmentListView(generics.ListAPIView):
    '''
    List appointments.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user)


class AppointmentCreateView(generics.ListCreateAPIView):
    '''
    Create a appointment.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AppointmentUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    '''
    Update and delete a appointment.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user)


class MonthClosingListView(generics.ListAPIView):
    '''
    Lists monthly cash closings.
    '''
    permission_classes = [IsAuthenticated]
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

        return MonthClosing.objects.filter(
            user=self.request.user,
            year=year
        ).order_by("month")


class MonthClosingCreateUpdateView(generics.ListCreateAPIView, generics.RetrieveUpdateDestroyAPIView):
    '''
    Creates and updates monthly cash closing data.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = MonthClosingSerializer

    def get_queryset(self):
        return MonthClosing.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        data = request.data
        data = perform_calculations(request.user, Revenue, Expense, data)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        data = request.data
        data = perform_calculations(request.user, Revenue, Expense, data)

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_200_OK)


class MonthClosingUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    '''
    Update and delete a month cash closing.
    '''
    permission_classes = [IsAuthenticated]
    serializer_class = MonthClosingSerializer

    def get_queryset(self):
        return MonthClosing.objects.filter(user=self.request.user)


class UpdateNetValuesView(APIView):
    """
    Updates net revenue values and recalculates month closing.
    """

    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):

        serializer = RevenueNetValueUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reference = serializer.validated_data["reference"]
        revenue_items = serializer.validated_data["revenue"]

        user = request.user
        months_to_update = set()

        with transaction.atomic():

            for item in revenue_items:
                try:
                    revenue = Revenue.objects.get(id=item["id"], user=user)

                    revenue.net_value = item["net_value"]
                    revenue.date = item["date"]
                    revenue.save()

                    months_to_update.add((revenue.date.month, revenue.date.year))

                except Revenue.DoesNotExist:
                    return Response(
                        {"detail": f"Revenue with id {item['id']} not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            for month, year in months_to_update:
                update_month_closing(user, month, year, reference)

            month_closing = MonthClosing.objects.get(
                user=user,
                month=month,
                year=year
            )

        return Response(
            {
                "detail": "Net values updated successfully.",
                "month_closing": MonthClosingSerializer(month_closing).data
            },
            status=status.HTTP_200_OK
        )


class ProfitListView(APIView):
    """
    Returns a list of monthly gross profits for the last 12 months.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        profit_data, labels = gross_profit_of_the_last_12_months(
            Revenue,
            Expense,
            user
        )

        return Response({"profit": profit_data, "labels": labels})
