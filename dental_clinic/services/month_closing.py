from dental_clinic.models import Expense, Revenue, MonthClosing
from django.db.models import Sum


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
