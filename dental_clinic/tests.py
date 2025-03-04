from django.test import TestCase

from django.test import TestCase
from django.utils.timezone import now
from rest_framework.test import APIClient
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils.timezone import now
from rest_framework import status
from dental_clinic.utils import month_names
from .models import RevenueTest, ExpenseTest

class ProfitTestListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Specific dates for testing
        dates = [
            now().replace(month=1, day=15),
            now().replace(month=2, day=15),
            now().replace(month=3, day=15)
        ]

        # Create fixed revenue for January, February, March
        revenues = [1000, 1500, 2000]
        for date, value in zip(dates, revenues):
            RevenueTest.objects.create(
                date=date,
                name=f"Receita {date.month}",
                net_value=value,
                value=value,
                installments=1
            )

        # Create fixed expenses for January, February, March
        expenses = [500, 1200, 1800]
        for date, value in zip(dates, expenses):
            ExpenseTest.objects.create(
                date=date,
                name=f"Despesa {date.month}",
                value=value,

                year=2025,
                month=f"Mês {date.month}",
                is_paid=True
            )

    def test_profit_calculation(self):
        response = self.client.get('/api/dental/test/profit_list/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('profit', data)
        self.assertIn('labels', data)

        self.assertGreaterEqual(len(data['profit']), 3)
        self.assertGreaterEqual(len(data['labels']), 3)

        expected_profits = [500, 300, 200]
        self.assertEqual(data['profit'][-3:], expected_profits)

    def test_labels_order(self):
        response = self.client.get('/api/dental/test/profit_list/')
        data = response.json()

        expected_labels = ["Janeiro", "Fevereiro", "Março"]
        self.assertTrue(all(label in data['labels'] for label in expected_labels))

    def test_last_12_months_data(self):
        '''
        Test that last_12_months_dataCreate income and expenses for the last
        14 months and test if the last 12 months are returned.
        '''
        start_date = now().replace(month=3, day=15) # staring March

        # Creating data
        for i in range(14):
            date = start_date + relativedelta(months=i)
            revenue_value = 1200
            expense_value = 200

            RevenueTest.objects.create(
                date=date,
                name=f"Receita {i+1}",
                net_value=revenue_value,
                value=revenue_value,
                installments=1
            )

            ExpenseTest.objects.create(
                date=date,
                name=f"Despesa {i+1}",
                value=expense_value,
                year=date.year,
                month=month_names[date.month - 1],
                is_paid=True
            )

        response = self.client.get('/api/dental/test/profit_list/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data['profit']), 12)
        self.assertEqual(len(data['labels']), 12)
