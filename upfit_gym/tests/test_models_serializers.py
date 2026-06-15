from datetime import date

from django.test import TestCase

from upfit_gym.serializers import CustomerSerializer, ExpenseSerializer, RevenueSerializer
from upfit_gym.tests.factories import (
    create_customer,
    create_expense,
    create_revenue,
    create_user,
)


class UpfitModelTest(TestCase):
    def test_string_representations(self):
        user = create_user()
        customer = create_customer(user=user, name="Ana")
        revenue = create_revenue(user=user, customer=customer)
        expense = create_expense(user=user, name="Aluguel")

        self.assertEqual(str(customer), "Ana")
        self.assertEqual(str(revenue), "Ana")
        self.assertEqual(str(expense), "Aluguel")


class UpfitSerializerTest(TestCase):
    def test_customer_serializer_creates_customer_with_read_only_user_supplied_later(self):
        user = create_user()
        serializer = CustomerSerializer(data={
            "name": "Ana",
            "frequency": "2x",
            "start": "2026-06-15",
            "plan": "Mensal",
            "value": 200,
            "status": "Ativo",
            "notes": "test",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        customer = serializer.save(user=user)

        self.assertEqual(customer.user, user)
        self.assertEqual(customer.name, "Ana")

    def test_revenue_serializer_creates_revenue(self):
        user = create_user()
        customer = create_customer(user=user)
        serializer = RevenueSerializer(data={
            "customer": customer.id,
            "year": 2026,
            "month": "Junho",
            "payment_day": 10,
            "value": 200,
            "paid": "Pago",
            "notes": "test",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        revenue = serializer.save(user=user)

        self.assertEqual(revenue.customer, customer)
        self.assertEqual(revenue.value, 200)

    def test_expense_serializer_rejects_missing_required_fields(self):
        serializer = ExpenseSerializer(data={
            "name": "Aluguel",
            "date": date(2026, 6, 15),
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("year", serializer.errors)
        self.assertIn("month", serializer.errors)
