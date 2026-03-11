from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model

from dental_clinic.models import Revenue, Expense, MonthClosing
from dental_clinic.services.month_closing import MonthClosingService


User = get_user_model()


class MonthClosingServiceTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create_user(
            username="doctor",
            password="123456"
        )

        # -------------------------
        # Revenues (June)
        # -------------------------

        Revenue.objects.create(
            user=cls.user,
            date=date(2025, 6, 10),
            release_date=date(2025, 6, 10),
            name="Paciente A",
            cpf="00000000000",
            nf=False,
            procedure="Cleaning",
            payment="cash",
            installments=1,
            value=100,
            net_value=90,
            notes="teste"
        )

        Revenue.objects.create(
            user=cls.user,
            date=date(2025, 6, 15),
            release_date=date(2025, 6, 15),
            name="Paciente B",
            cpf="11111111111",
            nf=False,
            procedure="Implant",
            payment="credit",
            installments=1,
            value=800,
            net_value=700,
            notes="teste"
        )

        # -------------------------
        # Expenses (July)
        # -------------------------

        Expense.objects.create(
            user=cls.user,
            year=2025,
            month="Julho",
            name="Aluguel",
            installments="1",
            date=date(2025, 7, 5),
            value=200,
            is_paid=True,
            notes="teste"
        )

        Expense.objects.create(
            user=cls.user,
            year=2025,
            month="Julho",
            name="Energia",
            installments="1",
            date=date(2025, 7, 10),
            value=100,
            is_paid=True,
            notes="teste"
        )

    # -------------------------------------------------
    # sum values
    # -------------------------------------------------

    def test_sum_values(self):

        total = MonthClosingService._sum_values(
            self.user,
            Revenue,
            6,
            2025
        )

        self.assertEqual(total, 900)

    # -------------------------------------------------
    # calculate
    # -------------------------------------------------

    def test_calculate_month_closing(self):

        data = {
            "month": 6,
            "year": 2025,
            "bank_value": 200,
            "cash_value": 100,
            "card_value": 300,
            "card_value_next_month": 50,
            "other_revenue": 0
        }

        result = MonthClosingService.calculate(self.user, data)

        self.assertEqual(result["gross_revenue"], 900)
        self.assertEqual(result["net_revenue"], 790)

        # expenses next month (July)
        self.assertEqual(result["expenses"], 300)

        # half expenses
        self.assertEqual(result["other_revenue"], 150)

        # net profit = net_revenue - half_expenses
        self.assertEqual(result["net_profit"], 640)

    # -------------------------------------------------
    # december edge case
    # -------------------------------------------------

    def test_calculate_december_next_year(self):

        Revenue.objects.create(
            user=self.user,
            date=date(2025, 12, 10),
            release_date=date(2025, 12, 10),
            name="Paciente C",
            cpf="22222222222",
            nf=False,
            procedure="Cleaning",
            payment="cash",
            installments=1,
            value=500,
            net_value=450,
            notes="teste"
        )

        Expense.objects.create(
            user=self.user,
            year=2026,
            month="Janeiro",
            name="Material",
            installments="1",
            date=date(2026, 1, 5),
            value=200,
            is_paid=True,
            notes="teste"
        )

        data = {
            "month": 12,
            "year": 2025,
            "bank_value": 0,
            "cash_value": 0,
            "card_value": 0,
            "card_value_next_month": 0,
            "other_revenue": 0
        }

        result = MonthClosingService.calculate(self.user, data)

        self.assertEqual(result["gross_revenue"], 500)
        self.assertEqual(result["expenses"], 200)

    # -------------------------------------------------
    # recalculate
    # -------------------------------------------------

    def test_recalculate_creates_month_closing(self):

        result = MonthClosingService.recalculate(
            self.user,
            6,
            2025,
            reference="test"
        )

        self.assertIsInstance(result, MonthClosing)

        self.assertEqual(result.gross_revenue, 900)
        self.assertEqual(result.net_revenue, 790)
        self.assertEqual(result.expenses, 0)

    # -------------------------------------------------
    # recalculate update existing
    # -------------------------------------------------

    def test_recalculate_updates_existing(self):

        MonthClosing.objects.create(
            user=self.user,
            month=6,
            year=2025,
            reference="old",
            gross_revenue=0,
            net_revenue=0,
            expenses=0,
            net_profit=0
        )

        result = MonthClosingService.recalculate(
            self.user,
            6,
            2025,
            reference="updated"
        )

        self.assertEqual(result.reference, "updated")
        self.assertEqual(result.gross_revenue, 900)