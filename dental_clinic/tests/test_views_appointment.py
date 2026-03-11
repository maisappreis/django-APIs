from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from dental_clinic.models import Appointment


User = get_user_model()


class AppointmentViewTest(APITestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create_user(
            username="doctor",
            password="123456"
        )

        cls.appointment = Appointment.objects.create(
            user=cls.user,
            name="Paciente A",
            date=timezone.now().date(),
            time="10:00",
            notes="teste"
        )

    def setUp(self):

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # -------------------------------------------------
    # list appointments
    # -------------------------------------------------

    def test_list_appointments(self):

        url = reverse("dental:appointment-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data["results"]

        self.assertEqual(len(results), 1)

    # -------------------------------------------------
    # create appointment
    # -------------------------------------------------

    def test_create_appointment(self):

        url = reverse("dental:appointment-create")

        data = {
            "name": "Paciente B",
            "date": "2025-06-10",
            "time": "14:00",
            "notes": "teste"
        }

        initial_count = Appointment.objects.count()

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.count(), initial_count + 1)

    # -------------------------------------------------
    # update appointment
    # -------------------------------------------------

    def test_update_appointment(self):

        url = reverse("dental:appointment-update-destroy", args=[self.appointment.id])

        data = {
            "name": "Paciente A",
            "date": str(self.appointment.date),
            "time": "11:00",
            "notes": "updated"
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.time, "11:00")

    # -------------------------------------------------
    # delete appointment
    # -------------------------------------------------

    def test_delete_appointment(self):

        url = reverse("dental:appointment-update-destroy", args=[self.appointment.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Appointment.objects.count(), 0)

    # -------------------------------------------------
    # user isolation
    # -------------------------------------------------

    def test_user_cannot_update_other_user_appointment(self):

        other_user = User.objects.create_user(
            username="other",
            password="123"
        )

        other_appointment = Appointment.objects.create(
            user=other_user,
            name="Paciente X",
            date=timezone.now().date(),
            time="15:00",
            notes=""
        )

        url = reverse("dental:appointment-update-destroy", args=[other_appointment.id])

        response = self.client.patch(
            url,
            {"time": "16:00"},
            format="json"
        )

        self.assertEqual(response.status_code, 404)