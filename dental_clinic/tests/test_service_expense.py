from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model

from dental_clinic.models import Expense
from dental_clinic.services.expense import ExpenseService


User = get_user_model()


class ExpenseServiceTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create_user(
            username="doctor",
            password="123456"
        )

    # -------------------------------------------------
    # create expense without installments
    # -------------------------------------------------

    def test_create_single_expense(self):

        data = {
            "year": 2025,
            "month": "Junho",
            "name": "Internet",
            "installments": None,
            "date": date(2025, 6, 10),
            "value": 120,
            "is_paid": False,
            "notes": "teste"
        }

        result = ExpenseService.create_expenses(self.user, data)

        self.assertEqual(len(result), 1)

        expense = result[0]

        self.assertEqual(expense.name, "Internet")
        self.assertEqual(expense.value, 120)

        self.assertEqual(Expense.objects.count(), 1)

    # -------------------------------------------------
    # create installments
    # -------------------------------------------------

    def test_create_installments(self):

        data = {
            "year": 2025,
            "month": "Junho",
            "name": "Equipamento",
            "installments": "3",
            "date": date(2025, 6, 10),
            "value": 300,
            "is_paid": False,
            "notes": "teste"
        }

        result = ExpenseService.create_expenses(self.user, data)

        self.assertEqual(len(result), 3)

        self.assertEqual(Expense.objects.count(), 3)

        first = result[0]
        second = result[1]
        third = result[2]

        self.assertEqual(first.installments, "1/3")
        self.assertEqual(second.installments, "2/3")
        self.assertEqual(third.installments, "3/3")

        self.assertEqual(first.date.month, 6)
        self.assertEqual(second.date.month, 7)
        self.assertEqual(third.date.month, 8)

        self.assertEqual(first.year, 2025)
        self.assertEqual(second.year, 2025)
        self.assertEqual(third.year, 2025)

    # -------------------------------------------------
    # month generation
    # -------------------------------------------------

    def test_month_is_generated_in_portuguese(self):

        data = {
            "year": 2025,
            "month": "Junho",
            "name": "Software",
            "installments": "2",
            "date": date(2025, 6, 10),
            "value": 100,
            "is_paid": False,
            "notes": "teste"
        }

        result = ExpenseService.create_expenses(self.user, data)

        first = result[0]
        second = result[1]

        self.assertEqual(first.month, "Junho")
        self.assertEqual(second.month, "Julho")

    # -------------------------------------------------
    # year change when installments pass december
    # -------------------------------------------------

    def test_year_changes_when_installments_cross_year(self):

        data = {
            "year": 2025,
            "month": "Novembro",
            "name": "Curso",
            "installments": "3",
            "date": date(2025, 11, 10),
            "value": 500,
            "is_paid": False,
            "notes": "teste"
        }

        result = ExpenseService.create_expenses(self.user, data)

        first = result[0]
        second = result[1]
        third = result[2]

        self.assertEqual(first.year, 2025)
        self.assertEqual(second.year, 2025)
        self.assertEqual(third.year, 2026)