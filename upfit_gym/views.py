from datetime import timedelta
from django.utils import timezone

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from upfit_gym.services import ExpenseService
from upfit_gym.serializers import *
from upfit_gym.models import *
from upfit_gym.mixins import *


class CustomerListView(UserQuerySetMixin, generics.ListAPIView):
    '''
    List customers.
    '''
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerCreateView(UserQuerySetMixin, generics.ListCreateAPIView):
    '''
    Create a customer.
    '''
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerUpdateDestroyView(UserQuerySetMixin, generics.RetrieveUpdateDestroyAPIView):
    '''
    Update and delete a customer.
    '''
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class RevenueListView(UserQuerySetMixin, generics.ListAPIView):
    '''
    List revenues.
    '''
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class RevenueCreateView(UserQuerySetMixin, generics.ListCreateAPIView):
    '''
    Create a revenue.
    '''
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class RevenueUpdateDestroyView(UserQuerySetMixin, generics.RetrieveUpdateDestroyAPIView):
    '''
    Update and delete a revenue.
    '''
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer


class ExpenseListView(UserQuerySetMixin, generics.ListAPIView):
    '''
    Lists expenses.
    '''
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

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
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
