from unittest.mock import patch

from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient
from rest_framework import status


User = get_user_model()


class DashboardChartsViewTest(APITestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create_user(
            username="doctor",
            password="123456"
        )

    def setUp(self):

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # -------------------------------------------------
    # success
    # -------------------------------------------------

    @patch("dental_clinic.services.dashboard.DashboardService.get_charts")
    def test_get_dashboard_charts(self, mock_get_charts):

        mock_get_charts.return_value = {
            "revenue_chart": [100, 200, 300],
            "expenses_chart": [50, 80, 120]
        }

        url = reverse("dental:dashboard-charts-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            response.data,
            {
                "revenue_chart": [100, 200, 300],
                "expenses_chart": [50, 80, 120]
            }
        )

        mock_get_charts.assert_called_once_with(self.user)

    # -------------------------------------------------
    # authentication required
    # -------------------------------------------------

    def test_authentication_required(self):

        client = APIClient()

        url = reverse("dental:dashboard-charts-list")

        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)