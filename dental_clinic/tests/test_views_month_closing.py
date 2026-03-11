from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from dental_clinic.models import MonthClosing


User = get_user_model()


class MonthClosingViewTest(APITestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create_user(
            username="doctor",
            password="123456"
        )

        cls.month_closing = MonthClosing.objects.create(
            user=cls.user,
            reference="Jan 2025",
            month=1,
            year=2025,
            gross_revenue=1000,
            net_revenue=900,
            expenses=400,
            net_profit=500,
            bank_value=200,
            cash_value=100,
            card_value=300,
            card_value_next_month=50,
            other_revenue=0,
            balance=150
        )

    def setUp(self):

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # -------------------------------------------------
    # list month closings
    # -------------------------------------------------

    def test_list_month_closings(self):

        url = reverse("dental:month-closing-list")

        response = self.client.get(url, {"year": 2025})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data["results"]

        self.assertEqual(len(results), 1)

    def test_list_requires_year_param(self):

        url = reverse("dental:month-closing-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_invalid_year(self):

        url = reverse("dental:month-closing-list")

        response = self.client.get(url, {"year": "abc"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------
    # create month closing
    # -------------------------------------------------

    def test_create_month_closing(self):

        url = reverse("dental:month-closing-create")

        data = {
            "reference": "Feb 2025",
            "month": 2,
            "year": 2025,
            "bank_value": 100,
            "cash_value": 100,
            "card_value": 200,
            "card_value_next_month": 50,
            "other_revenue": 0
        }

        initial_count = MonthClosing.objects.count()

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MonthClosing.objects.count(), initial_count + 1)

    # -------------------------------------------------
    # update month closing
    # -------------------------------------------------

    def test_update_month_closing(self):

        url = reverse(
            "dental:month-closing-update-destroy",
            args=[self.month_closing.id]
        )

        data = {
            "reference": "Jan 2025",
            "month": 1,
            "year": 2025,
            "bank_value": 500,
            "cash_value": 100,
            "card_value": 200,
            "card_value_next_month": 50,
            "other_revenue": 0
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.month_closing.refresh_from_db()

        self.assertEqual(self.month_closing.bank_value, 500)

    # -------------------------------------------------
    # delete month closing
    # -------------------------------------------------

    def test_delete_month_closing(self):

        url = reverse(
            "dental:month-closing-update-destroy",
            args=[self.month_closing.id]
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(MonthClosing.objects.count(), 0)

    # -------------------------------------------------
    # user isolation
    # -------------------------------------------------

    def test_user_cannot_update_other_user_month_closing(self):

        other_user = User.objects.create_user(
            username="other",
            password="123"
        )

        other_closing = MonthClosing.objects.create(
            user=other_user,
            reference="Mar 2025",
            month=3,
            year=2025,
            gross_revenue=100,
            net_revenue=80,
            expenses=50,
            net_profit=30
        )

        url = reverse(
            "dental:month-closing-update-destroy",
            args=[other_closing.id]
        )

        response = self.client.patch(
            url,
            {"bank_value": 999},
            format="json"
        )

        self.assertEqual(response.status_code, 404)