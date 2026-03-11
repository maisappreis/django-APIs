from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from dental_clinic.models import Revenue, Expense
from dental_clinic.services.dashboard import DashboardService


User = get_user_model()


class DashboardServiceTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create_user(
            username="doctor",
            password="123456"
        )

        today = timezone.now().date()

        # -------------------------
        # Revenues
        # -------------------------

        Revenue.objects.create(
            user=cls.user,
            date=today,
            release_date=today,
            name="Paciente A",
            cpf="00000000000",
            nf=False,
            procedure="Cleaning",
            payment="cash",
            installments=1,
            value=100,
            net_value=100,
            notes="teste"
        )

        Revenue.objects.create(
            user=cls.user,
            date=today,
            release_date=today,
            name="Paciente B",
            cpf="11111111111",
            nf=False,
            procedure="Cleaning",
            payment="credit",
            installments=1,
            value=150,
            net_value=150,
            notes="teste"
        )

        Revenue.objects.create(
            user=cls.user,
            date=today,
            release_date=today,
            name="Paciente C",
            cpf="22222222222",
            nf=False,
            procedure="Implant",
            payment="credit",
            installments=1,
            value=800,
            net_value=800,
            notes="teste"
        )

        # -------------------------
        # Expenses
        # -------------------------

        Expense.objects.create(
            user=cls.user,
            year=today.year,
            month="Jun",
            name="Material odontológico",
            installments="1",
            date=today,
            value=200,
            is_paid=True,
            notes="teste"
        )

        Expense.objects.create(
            user=cls.user,
            year=today.year,
            month="Jun",
            name="Energia",
            installments="1",
            date=today,
            value=50,
            is_paid=True,
            notes="teste"
        )

        cls.start_date = today - timedelta(days=365)

    # -------------------------------------------------
    # last 12 months
    # -------------------------------------------------

    def test_last_12_months(self):

        months = DashboardService._last_12_months()

        self.assertEqual(len(months), 12)

        for i in range(11):
            self.assertLess(months[i], months[i + 1])

    # -------------------------------------------------
    # most performed procedures
    # -------------------------------------------------

    def test_most_performed_procedures(self):

        result = DashboardService._most_performed_procedures(
            self.user,
            self.start_date
        )

        self.assertIn("Cleaning", result["labels"])
        self.assertIn("Implant", result["labels"])

        index = result["labels"].index("Cleaning")

        self.assertEqual(result["data"][index], 2)

    # -------------------------------------------------
    # number of procedures
    # -------------------------------------------------

    def test_number_of_procedures(self):

        result = DashboardService._number_of_procedures(
            self.user,
            self.start_date
        )

        self.assertEqual(len(result["labels"]), 12)
        self.assertEqual(len(result["data"]), 12)

        self.assertEqual(sum(result["data"]), 3)

    # -------------------------------------------------
    # monthly profit
    # -------------------------------------------------

    def test_monthly_profit(self):

        result = DashboardService._monthly_profit(
            self.user,
            self.start_date
        )

        self.assertEqual(len(result["labels"]), 12)

        # revenue = 100 + 150 + 800 = 1050
        # expense = 200 + 50 = 250
        # profit = 800

        self.assertIn(800, result["data"])

    # -------------------------------------------------
    # revenue vs expense
    # -------------------------------------------------

    def test_revenue_vs_expense(self):

        result = DashboardService._revenue_vs_expense(
            self.user,
            self.start_date
        )

        revenue = result["data"]["revenue"]
        expense = result["data"]["expense"]

        self.assertEqual(sum(revenue), 1050)
        self.assertEqual(sum(expense), 250)

    # -------------------------------------------------
    # full dashboard
    # -------------------------------------------------

    def test_get_charts(self):

        result = DashboardService.get_charts(self.user)

        self.assertIn("most_performed_procedures", result)
        self.assertIn("number_of_procedures", result)
        self.assertIn("monthly_profit", result)
        self.assertIn("revenue_versus_expense", result)