from datetime import date

from django.test import TestCase
from django.utils import timezone

from upfit_gym.models import Expense
from upfit_gym.services import DashboardService, ExpenseService
from upfit_gym.tests.factories import (
    create_customer,
    create_expense,
    create_revenue,
    create_user,
)


class ExpenseServiceTest(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_create_single_expense_when_installments_is_blank(self):
        expenses = ExpenseService.create_expenses(self.user, {
            "name": "Internet",
            "year": 2026,
            "month": "Junho",
            "date": date(2026, 6, 10),
            "installments": "",
            "value": 120,
            "paid": "A pagar",
            "notes": "test",
        })

        self.assertEqual(len(expenses), 1)
        self.assertEqual(expenses[0].name, "Internet")
        self.assertEqual(Expense.objects.count(), 1)

    def test_create_installments_updates_month_year_and_installment_label(self):
        expenses = ExpenseService.create_expenses(self.user, {
            "name": "Equipamento",
            "year": 2026,
            "month": "Novembro",
            "date": date(2026, 11, 10),
            "installments": "3",
            "value": 300,
            "paid": "A pagar",
            "notes": "test",
        })

        self.assertEqual(len(expenses), 3)
        self.assertEqual([expense.installments for expense in expenses], ["1/3", "2/3", "3/3"])
        self.assertEqual([expense.month for expense in expenses], ["Novembro", "Dezembro", "Janeiro"])
        self.assertEqual([expense.year for expense in expenses], [2026, 2026, 2027])


class DashboardServiceTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user()
        self.start_date = timezone.now() - timezone.timedelta(days=365)

    def test_empty_dashboard_returns_empty_charts(self):
        charts = DashboardService.get_charts(self.user)

        self.assertEqual(charts["active_inactive_customers"], {"labels": [], "data": []})
        self.assertEqual(charts["number_of_active_customer_per_month"], {"labels": [], "data": []})
        self.assertEqual(charts["monthly_profit"], {"labels": [], "data": []})
        self.assertEqual(
            charts["revenue_versus_expense"],
            {"labels": [], "data": {"revenue": [], "expense": []}},
        )

    def test_dashboard_charts_with_data_ignore_other_users(self):
        active_customer = create_customer(
            user=self.user,
            name="Active",
            status="Ativo",
            start=date(2026, 6, 1),
        )
        create_customer(
            user=self.user,
            name="Inactive",
            status="Inativo",
            start=date(2026, 6, 2),
        )
        create_customer(
            user=self.other_user,
            name="Other",
            status="Ativo",
            start=date(2026, 6, 3),
        )
        create_revenue(
            user=self.user,
            customer=active_customer,
            year=2026,
            month="Junho",
            value=300,
        )
        inactive_customer = create_customer(
            user=self.user,
            name="Inactive Revenue",
            status="Inativo",
            start=date(2026, 1, 1),
        )
        create_revenue(
            user=self.user,
            customer=inactive_customer,
            year=2026,
            month="Junho",
            value=310,
        )
        create_expense(
            user=self.user,
            year=2026,
            month="Junho",
            date=date(2026, 6, 10),
            value=120,
        )
        create_expense(
            user=self.other_user,
            year=2026,
            month="Junho",
            date=date(2026, 6, 10),
            value=999,
        )

        active_inactive = DashboardService._active_inactive_customers(
            self.user,
            self.start_date,
        )
        active_per_month = DashboardService._number_of_active_customer_per_month(
            self.user,
            self.start_date,
        )
        monthly_profit = DashboardService._monthly_profit(self.user, self.start_date)
        revenue_vs_expense = DashboardService._revenue_vs_expense(
            self.user,
            self.start_date,
        )

        self.assertEqual(active_inactive["labels"], ["Ativos", "Inativos"])
        self.assertEqual(active_inactive["data"], [1, 2])
        self.assertEqual(sum(active_per_month["data"]), 2)
        self.assertIn(490, monthly_profit["data"])
        self.assertEqual(sum(revenue_vs_expense["data"]["revenue"]), 610)
        self.assertEqual(sum(revenue_vs_expense["data"]["expense"]), 120)

    def test_active_customers_per_month_counts_revenue_customers(self):
        active_july_1 = create_customer(
            user=self.user,
            name="Active July 1",
            status="Ativo",
            start=date(2024, 1, 1),
        )
        active_july_2 = create_customer(
            user=self.user,
            name="Active July 2",
            status="Ativo",
            start=date(2024, 2, 1),
        )
        currently_inactive_july = create_customer(
            user=self.user,
            name="Currently Inactive July",
            status="Inativo",
            start=date(2024, 3, 1),
        )
        other_user_customer = create_customer(
            user=self.other_user,
            name="Other July",
            status="Ativo",
            start=date(2024, 4, 1),
        )

        create_revenue(
            user=self.user,
            customer=active_july_1,
            year=2026,
            month="Julho",
            value=200,
        )
        create_revenue(
            user=self.user,
            customer=active_july_2,
            year=2026,
            month="Julho",
            value=220,
        )
        create_revenue(
            user=self.user,
            customer=currently_inactive_july,
            year=2026,
            month="Julho",
            value=240,
        )
        create_revenue(
            user=self.other_user,
            customer=other_user_customer,
            year=2026,
            month="Julho",
            value=260,
        )

        chart = DashboardService._number_of_active_customer_per_month(
            self.user,
            self.start_date,
        )

        july_index = chart["labels"].index("Jul 2026")
        self.assertEqual(chart["data"][july_index], 3)

    def test_dashboard_helpers_return_labels_and_maps(self):
        months = DashboardService._last_12_months()

        self.assertEqual(len(months), 12)
        self.assertEqual(DashboardService._month_label(months[-1]), f"{DashboardService._month_label(months[-1])}")
        self.assertEqual(DashboardService._empty_chart(), {"labels": [], "data": []})
