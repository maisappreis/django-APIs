from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from dental_clinic.models import Revenue
from dental_clinic.services.revenue import RevenueService


User = get_user_model()


class RevenueServiceTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create_user(
            username="doctor",
            password="123456"
        )

        cls.revenue1 = Revenue.objects.create(
            user=cls.user,
            date=date(2025, 6, 10),
            release_date=date(2025, 6, 10),
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

        cls.revenue2 = Revenue.objects.create(
            user=cls.user,
            date=date(2025, 7, 10),
            release_date=date(2025, 7, 10),
            name="Paciente B",
            cpf="11111111111",
            nf=False,
            procedure="Implant",
            payment="credit",
            installments=1,
            value=800,
            net_value=700,
            notes="teste"
        )

    # -------------------------------------------------
    # update net values
    # -------------------------------------------------

    @patch("dental_clinic.services.revenue.MonthClosingService.recalculate")
    def test_update_net_values(self, mock_recalculate):

        mock_recalculate.return_value = {"status": "ok"}

        items = [
            {
                "id": self.revenue1.id,
                "net_value": 95,
                "date": date(2025, 6, 15)
            },
            {
                "id": self.revenue2.id,
                "net_value": 750,
                "date": date(2025, 7, 20)
            }
        ]

        result = RevenueService.update_net_values(
            self.user,
            items,
            reference="test"
        )

        self.revenue1.refresh_from_db()
        self.revenue2.refresh_from_db()

        self.assertEqual(self.revenue1.net_value, 95)
        self.assertEqual(self.revenue2.net_value, 750)

        self.assertEqual(self.revenue1.date, date(2025, 6, 15))
        self.assertEqual(self.revenue2.date, date(2025, 7, 20))

        self.assertTrue(mock_recalculate.called)

        self.assertEqual(result, {"status": "ok"})

    # -------------------------------------------------
    # revenue not found
    # -------------------------------------------------

    def test_update_net_values_revenue_not_found(self):

        items = [
            {
                "id": 999,
                "net_value": 100,
                "date": date(2025, 6, 15)
            }
        ]

        with self.assertRaises(ValueError):

            RevenueService.update_net_values(
                self.user,
                items,
                reference="test"
            )

    # -------------------------------------------------
    # recalculation called for each month
    # -------------------------------------------------

    @patch("dental_clinic.services.revenue.MonthClosingService.recalculate")
    def test_recalculate_called_for_each_month(self, mock_recalculate):

        mock_recalculate.return_value = {"status": "ok"}

        items = [
            {
                "id": self.revenue1.id,
                "net_value": 100,
                "date": date(2025, 6, 10)
            },
            {
                "id": self.revenue2.id,
                "net_value": 800,
                "date": date(2025, 7, 10)
            }
        ]

        RevenueService.update_net_values(
            self.user,
            items,
            reference="test"
        )

        self.assertEqual(mock_recalculate.call_count, 2)