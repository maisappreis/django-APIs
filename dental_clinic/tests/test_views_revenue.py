from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from dental_clinic.models import Revenue


User = get_user_model()


class RevenueViewTest(APITestCase):

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
          payment="cash",
          installments=1,
          value=100,
          net_value=90,
          notes="teste"
      )


    def setUp(self):

      self.client = APIClient()
      self.client.force_authenticate(user=self.user)

    # -------------------------------------------------
    # list revenues
    # -------------------------------------------------

    def test_list_revenues(self):

      url = reverse("dental:revenue-list")

      response = self.client.get(url)

      self.assertEqual(response.status_code, status.HTTP_200_OK)

      if isinstance(response.data, list):
          results = response.data
      else:
          results = response.data["results"]

      self.assertEqual(len(results), 1)

    # -------------------------------------------------
    # create revenue
    # -------------------------------------------------

    def test_create_revenue(self):

        url = reverse("dental:revenue-create")

        data = {
            "date": "2025-06-10",
            "release_date": "2025-06-10",
            "name": "Paciente C",
            "cpf": "11111111111",
            "nf": False,
            "procedure": "Implant",
            "payment": "credit",
            "installments": 1,
            "value": 800,
            "net_value": 700,
            "notes": "teste"
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Revenue.objects.count(), 2)

    # -------------------------------------------------
    # update revenue
    # -------------------------------------------------

    def test_update_revenue(self):
      url = reverse("dental:revenue-update-destroy", args=[self.revenue.id])

      data = {
          "date": "2025-06-15",
          "release_date": "2025-06-10",
          "name": "Paciente A",
          "cpf": "00000000000",
          "nf": False,
          "procedure": "Cleaning",
          "payment": "cash",
          "installments": 1,
          "value": 150,
          "net_value": 120,
          "notes": "updated"
      }

      response = self.client.patch(url, data, format="json")

      self.assertEqual(response.status_code, 200)


    def test_user_cannot_update_other_user_revenue(self):
      other_user = User.objects.create_user(username="other", password="123")

      other_revenue = Revenue.objects.create(
          user=other_user,
          date=timezone.now().date(),
          name="Paciente B",
          cpf="111",
          nf=False,
          procedure="Extraction",
          payment="cash",
          value=200
      )

      url = reverse("dental:revenue-update-destroy", args=[other_revenue.id])

      response = self.client.put(url, {"value": 300}, format="json")

      self.assertEqual(response.status_code, 404)

    # -------------------------------------------------
    # delete revenue
    # -------------------------------------------------

    def test_delete_revenue(self):

        url = reverse("dental:revenue-update-destroy", args=[self.revenue.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(Revenue.objects.count(), 0)

    # -------------------------------------------------
    # authentication required
    # -------------------------------------------------

    def test_authentication_required(self):

        client = APIClient()

        url = reverse("dental:revenue-list")

        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -------------------------------------------------
    # list only last 12 months
    # -------------------------------------------------

    def test_list_only_last_12_months(self):

      old_date = timezone.now().date() - timedelta(days=400)

      Revenue.objects.create(
          user=self.user,
          date=old_date,
          release_date=old_date,
          name="Paciente Antigo",
          cpf="99999999999",
          nf=False,
          procedure="Cleaning",
          payment="cash",
          installments=1,
          value=100,
          net_value=90,
          notes="old"
      )

      url = reverse("dental:revenue-list")

      response = self.client.get(url)

      self.assertEqual(response.status_code, 200)

      if isinstance(response.data, list):
          results = response.data
      else:
          results = response.data["results"]

      self.assertEqual(len(results), 1)