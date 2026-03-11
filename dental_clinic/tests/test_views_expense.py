from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from dental_clinic.models import Expense


User = get_user_model()


class ExpenseViewTest(APITestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create_user(
            username="doctor",
            password="123456"
        )

        today = timezone.now().date()

        cls.expense = Expense.objects.create(
            user=cls.user,
            year=today.year,
            month="Junho",
            name="Aluguel",
            installments=None,
            date=today,
            value=1000,
            is_paid=False,
            notes="teste"
        )

    def setUp(self):

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # -------------------------------------------------
    # list expenses
    # -------------------------------------------------

    def test_list_expenses(self):

        url = reverse("dental:expense-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data["results"]

        self.assertEqual(len(results), 1)

    # -------------------------------------------------
    # create expense
    # -------------------------------------------------

    def test_create_expense(self):

        url = reverse("dental:expense-create")

        data = {
            "year": 2025,
            "month": "Junho",
            "name": "Internet",
            "installments": None,
            "date": "2025-06-10",
            "value": 200,
            "is_paid": False,
            "notes": "teste"
        }

        initial_count = Expense.objects.count()

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Expense.objects.count(), initial_count + 1)

    # -------------------------------------------------
    # create installment expenses
    # -------------------------------------------------

    def test_create_installment_expenses(self):

        url = reverse("dental:expense-create")

        data = {
            "year": 2025,
            "month": "Junho",
            "name": "Equipamento",
            "installments": 3,
            "date": "2025-06-10",
            "value": 300,
            "is_paid": False,
            "notes": "teste"
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(len(response.data), 3)
        self.assertEqual(Expense.objects.filter(name="Equipamento").count(), 3)

    # -------------------------------------------------
    # update expense
    # -------------------------------------------------

    def test_update_expense(self):

        url = reverse("dental:expense-update-destroy", args=[self.expense.id])

        data = {
            "year": self.expense.year,
            "month": self.expense.month,
            "name": "Aluguel atualizado",
            "installments": None,
            "date": str(self.expense.date),
            "value": 1200,
            "is_paid": True,
            "notes": "updated"
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.expense.refresh_from_db()
        self.assertEqual(self.expense.value, 1200)

    # -------------------------------------------------
    # delete expense
    # -------------------------------------------------

    def test_delete_expense(self):

        url = reverse("dental:expense-update-destroy", args=[self.expense.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Expense.objects.count(), 0)

    # -------------------------------------------------
    # user isolation
    # -------------------------------------------------

    def test_user_cannot_update_other_user_expense(self):

        other_user = User.objects.create_user(username="other", password="123")

        other_expense = Expense.objects.create(
            user=other_user,
            year=2025,
            month="Junho",
            name="Despesa outro usuário",
            date=timezone.now().date(),
            value=500,
            is_paid=False
        )

        url = reverse("dental:expense-update-destroy", args=[other_expense.id])

        response = self.client.patch(url, {"value": 600}, format="json")

        self.assertEqual(response.status_code, 404)

    # -------------------------------------------------
    # last 12 months filter
    # -------------------------------------------------

    def test_list_only_last_12_months(self):

        old_date = timezone.now().date() - timedelta(days=400)

        Expense.objects.create(
            user=self.user,
            year=old_date.year,
            month="Janeiro",
            name="Despesa antiga",
            date=old_date,
            value=100,
            is_paid=False
        )

        url = reverse("dental:expense-list")

        response = self.client.get(url)

        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data["results"]

        self.assertEqual(len(results), 1)