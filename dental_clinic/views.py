from rest_framework import generics
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from dental_clinic.utils import createInstallments

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


class MonthClosingCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = MonthClosing.objects.all()
    serializer_class = MonthClosingSerializer

    # def create:

    # Preciso interceptar a view create, fazer os devidos cálculos,
    # e modificar os seguintes valores, que chegaram zerados,
    # para salvar no banco de dados.

    # Criar as funções de cálculos nos útils.

    # gross_revenue = 0
    # net_revenue = 0
    # expenses = 0
    # profit = 0

    # other_revenue = 0
    # balance = 0


class MonthClosingUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = MonthClosing.objects.all()
    serializer_class = MonthClosingSerializer

    # Precisará refazer os cálculos, e salvar atualizado.


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
    permission_classes = [IsAuthenticated]
    queryset = MonthClosingTest.objects.all()
    serializer_class = MonthClosingTestSerializer


class MonthClosingTestCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = MonthClosingTest.objects.all()
    serializer_class = MonthClosingTestSerializer

    # def create:

    # Preciso interceptar a view create, fazer os devidos cálculos,
    # e modificar os seguintes valores, que chegaram zerados,
    # para salvar no banco de dados.

    # Criar as funções de cálculos nos útils.

    # gross_revenue = 0
    # net_revenue = 0
    # expenses = 0
    # profit = 0

    # other_revenue = 0
    # balance = 0


class MonthClosingTestUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = MonthClosingTest.objects.all()
    serializer_class = MonthClosingTestSerializer

    # Precisará refazer os cálculos, e salvar atualizado.