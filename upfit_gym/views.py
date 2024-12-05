from rest_framework import generics
from datetime import timedelta
from django.utils import timezone
from .models import *
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from dental_clinic.utils import createInstallments

# Real views used by authenticated users.


class CustomerListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class RevenueListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer
    # TODO: incluir "date" em Revenue

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

    def get_queryset(self):
        twelve_months_ago = timezone.now() - timedelta(days=370)
        return Expense.objects.filter(date__gte=twelve_months_ago).order_by('-date')


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
