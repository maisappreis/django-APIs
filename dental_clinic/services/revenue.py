from dental_clinic.services.month_closing import MonthClosingService
from dental_clinic.models import Revenue
from django.db import transaction


class RevenueService:

    @staticmethod
    @transaction.atomic
    def update_net_values(user, revenue_items, reference):

        months_to_update = set()

        for item in revenue_items:

            revenue = Revenue.objects.filter(
                id=item["id"],
                user=user
            ).first()

            if not revenue:
                raise ValueError(f"Revenue with id {item['id']} not found.")

            revenue.net_value = item["net_value"]
            revenue.date = item["date"]
            revenue.save(update_fields=["net_value", "date"])

            months_to_update.add((revenue.date.month, revenue.date.year))

        month_closing = None

        for month, year in months_to_update:
            month_closing = MonthClosingService.recalculate(
                user,
                month,
                year,
                reference
            )

        return month_closing