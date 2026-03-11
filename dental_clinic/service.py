from dateutil.relativedelta import relativedelta
from dental_clinic.models import Expense, Revenue, MonthClosing
from babel.dates import format_date
from django.db.models import Sum
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


class ExpenseService:

    @staticmethod
    def create_expenses(user, validated_data):

        installments = validated_data.get("installments")

        if not installments:
            expense = Expense.objects.create(
                user=user,
                **validated_data
            )
            return [expense]

        return ExpenseService._create_installments(user, validated_data)


    @staticmethod
    def _create_installments(user, data):

        installments = int(data["installments"])
        initial_date = data["date"]

        created = []

        for i in range(installments):

            installment_data = data.copy()

            date_obj = initial_date + relativedelta(months=i)

            installment_data["installments"] = f"{i+1}/{installments}"
            installment_data["date"] = date_obj
            installment_data["month"] = format_date(date_obj, "MMMM", locale="pt_BR").capitalize()
            installment_data["year"] = date_obj.year

            expense = Expense.objects.create(
                user=user,
                **installment_data
            )

            created.append(expense)

        return created
    

class MonthClosingService:

    @staticmethod
    def calculate(user, data):

        month = data["month"]
        year = data["year"]

        bank_value = data.get("bank_value") or 0
        cash_value = data.get("cash_value") or 0
        card_value = data.get("card_value") or 0
        card_value_next_month = data.get("card_value_next_month") or 0
        other_revenue = data.get("other_revenue") or 0

        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        gross_revenue = MonthClosingService._sum_values(
            user, Revenue, month, year
        )

        net_revenue = MonthClosingService._sum_values(
            user, Revenue, month, year, "net_value"
        )

        expenses = MonthClosingService._sum_values(
            user, Expense, next_month, next_year
        )

        half_expenses = expenses / 2
        net_profit = net_revenue - half_expenses

        card_value_this_month = card_value - card_value_next_month

        balance = (
            bank_value +
            cash_value +
            card_value_this_month +
            other_revenue
        ) - (expenses + net_profit)

        return {
            **data,
            "gross_revenue": gross_revenue,
            "net_revenue": net_revenue,
            "expenses": expenses,
            "net_profit": net_profit,
            "balance": balance,
            "other_revenue": half_expenses
        }


    @staticmethod
    def _sum_values(user, model, month, year, field="value"):

        return model.objects.filter(
            user=user,
            date__month=month,
            date__year=year
        ).aggregate(total=Sum(field))["total"] or 0
    

    @staticmethod
    def recalculate(user, month, year, reference):

        gross_revenue = (
            Revenue.objects.filter(
                user=user,
                date__month=month,
                date__year=year
            ).aggregate(total=Sum("value"))["total"] or 0
        )

        net_revenue = (
            Revenue.objects.filter(
                user=user,
                date__month=month,
                date__year=year
            ).aggregate(total=Sum("net_value"))["total"] or 0
        )

        expenses = (
            Expense.objects.filter(
                user=user,
                date__month=month,
                date__year=year
            ).aggregate(total=Sum("value"))["total"] or 0
        )

        net_profit = net_revenue - expenses

        month_closing, _ = MonthClosing.objects.update_or_create(
            user=user,
            month=month,
            year=year,
            defaults={
                "reference": reference,
                "gross_revenue": gross_revenue,
                "net_revenue": net_revenue,
                "expenses": expenses,
                "net_profit": net_profit,
            },
        )

        return month_closing