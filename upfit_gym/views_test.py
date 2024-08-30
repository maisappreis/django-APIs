from rest_framework import generics
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from dental_clinic.utils import createInstallments

# Test views used by unauthenticated users test application, like a portfolio.


class CustomerTestListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = CustomerTest.objects.all()
    serializer_class = CustomerTestSerializer


class CustomerTestCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    queryset = CustomerTest.objects.all()
    serializer_class = CustomerTestSerializer


class CustomerTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = CustomerTest.objects.all()
    serializer_class = CustomerTestSerializer


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
