from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from dental_clinic.models import Revenue


User = get_user_model()


class UpdateNetValuesViewTest(APITestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create_user(
            username="doctor",
            password="123456"
        )

        today = timezone.now().date()

        cls.revenue = Revenue.objects.create(
            user=cls.user,
            date=today,
            release_date=today,
            name="Paciente A",
            cpf="00000000000",
            nf=False,
            procedure="Cleaning",
            payment="credit",
            installments=1,
            value=100,
            net_value=90,
            notes="teste"
        )

    def setUp(self):

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # -------------------------------------------------
    # success update
    # -------------------------------------------------

    def test_update_net_values_success(self):

        url = reverse("dental:update-net-values")

        data = {
            "reference": "Jan 2025",
            "revenue": [
                {
                    "id": self.revenue.id,
                    "net_value": 80,
                    "date": str(self.revenue.date)
                }
            ]
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.revenue.refresh_from_db()

        self.assertEqual(self.revenue.net_value, 80)
        self.assertEqual(
            response.data["detail"],
            "Net values updated successfully."
        )

        self.assertIn("month_closing", response.data)

    # -------------------------------------------------
    # revenue not found
    # -------------------------------------------------

    def test_update_net_values_revenue_not_found(self):

        url = reverse("dental:update-net-values")

        data = {
            "reference": "Jan 2025",
            "revenue": [
                {
                    "id": 9999,
                    "net_value": 50,
                    "date": "2025-01-10"
                }
            ]
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertIn("detail", response.data)

    # -------------------------------------------------
    # invalid serializer
    # -------------------------------------------------

    def test_update_net_values_invalid_payload(self):

        url = reverse("dental:update-net-values")

        data = {
            "reference": "Jan 2025",
            "revenue": [
                {
                    "id": self.revenue.id
                }
            ]
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------
    # authentication required
    # -------------------------------------------------

    def test_authentication_required(self):

        client = APIClient()

        url = reverse("dental:update-net-values")

        response = client.put(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)