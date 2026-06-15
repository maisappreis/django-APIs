from datetime import date
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from upfit_gym.models import Customer, Expense, Revenue
from upfit_gym.tests.factories import (
    create_customer,
    create_expense,
    create_revenue,
    create_user,
)


class UpfitViewTest(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user()
        self.customer = create_customer(user=self.user, name="Ana")
        self.revenue = create_revenue(user=self.user, customer=self.customer)
        self.expense = create_expense(user=self.user, name="Aluguel")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def get_customer_payload(self, **overrides):
        data = {
            "name": "Bia",
            "frequency": "3x",
            "start": "2026-06-20",
            "plan": "Mensal",
            "value": 220,
            "status": "Ativo",
            "notes": "test",
        }
        data.update(overrides)
        return data

    def get_revenue_payload(self, **overrides):
        data = {
            "customer": self.customer.id,
            "year": 2026,
            "month": "Julho",
            "payment_day": 15,
            "value": 220,
            "paid": "Pago",
            "notes": "test",
        }
        data.update(overrides)
        return data

    def get_expense_payload(self, **overrides):
        data = {
            "name": "Internet",
            "year": 2026,
            "month": "Junho",
            "date": "2026-06-15",
            "installments": "",
            "value": 120,
            "paid": "A pagar",
            "notes": "test",
        }
        data.update(overrides)
        return data

    def test_authentication_required(self):
        client = APIClient()

        response = client.get(reverse("upfit:customer-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_crud_and_user_isolation(self):
        other_customer = create_customer(user=self.other_user, name="Other")

        list_response = self.client.get(reverse("upfit:customer-list"))
        create_response = self.client.post(
            reverse("upfit:customer-create"),
            self.get_customer_payload(),
            format="json",
        )
        update_response = self.client.patch(
            reverse("upfit:customer-update-destroy", args=[self.customer.id]),
            {"value": 250},
            format="json",
        )
        forbidden_response = self.client.patch(
            reverse("upfit:customer-update-destroy", args=[other_customer.id]),
            {"value": 250},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(forbidden_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Customer.objects.filter(user=self.user).count(), 2)

    def test_revenue_crud_and_user_isolation(self):
        other_customer = create_customer(user=self.other_user, name="Other")
        other_revenue = create_revenue(user=self.other_user, customer=other_customer)

        list_response = self.client.get(reverse("upfit:revenue-list"))
        create_response = self.client.post(
            reverse("upfit:revenue-create"),
            self.get_revenue_payload(month="Agosto"),
            format="json",
        )
        update_response = self.client.patch(
            reverse("upfit:revenue-update-destroy", args=[self.revenue.id]),
            {"paid": "Link enviado"},
            format="json",
        )
        forbidden_response = self.client.patch(
            reverse("upfit:revenue-update-destroy", args=[other_revenue.id]),
            {"paid": "Pago"},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(forbidden_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Revenue.objects.filter(user=self.user).count(), 2)

    def test_expense_list_filters_old_items_and_create_supports_installments(self):
        old_date = timezone.now().date() - timezone.timedelta(days=400)
        create_expense(
            user=self.user,
            name="Old",
            year=old_date.year,
            month="Janeiro",
            date=old_date,
            value=50,
        )

        list_response = self.client.get(reverse("upfit:expense-list"))
        create_response = self.client.post(
            reverse("upfit:expense-create"),
            self.get_expense_payload(
                name="Equipamento",
                installments="2",
                date="2026-11-15",
                month="Novembro",
                paid="Pago",
            ),
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(create_response.data), 2)
        self.assertEqual(Expense.objects.filter(name="Equipamento").count(), 2)

    def test_expense_update_delete_and_user_isolation(self):
        other_expense = create_expense(user=self.other_user, name="Other")

        update_response = self.client.patch(
            reverse("upfit:expense-update-destroy", args=[self.expense.id]),
            {"paid": "Pago"},
            format="json",
        )
        forbidden_response = self.client.patch(
            reverse("upfit:expense-update-destroy", args=[other_expense.id]),
            {"paid": "Pago"},
            format="json",
        )
        delete_response = self.client.delete(
            reverse("upfit:expense-update-destroy", args=[self.expense.id]),
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(forbidden_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Expense.objects.filter(id=self.expense.id).exists())

    @patch("upfit_gym.views.DashboardService.get_charts")
    def test_dashboard_charts_endpoint(self, get_charts):
        get_charts.return_value = {"monthly_profit": {"labels": [], "data": []}}

        response = self.client.get(reverse("upfit:dashboard-charts-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"monthly_profit": {"labels": [], "data": []}})
        get_charts.assert_called_once_with(self.user)
