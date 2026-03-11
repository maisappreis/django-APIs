from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from dental_clinic.models import Revenue, Expense


MONTH_LABELS = [
    "Jan", "Fev", "Mar", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Set", "Out", "Nov", "Dez"
]


class DashboardService:

    @staticmethod
    def get_charts(user):

        today = timezone.now()
        twelve_months_ago = today - timedelta(days=365)

        return {
            "most_performed_procedures": DashboardService._most_performed_procedures(user, twelve_months_ago),
            "number_of_procedures": DashboardService._number_of_procedures(user, twelve_months_ago),
            "monthly_profit": DashboardService._monthly_profit(user, twelve_months_ago),
            "revenue_versus_expense": DashboardService._revenue_vs_expense(user, twelve_months_ago),
        }
    

    @staticmethod
    def _last_12_months():

        today = timezone.now().replace(day=1)

        months = []

        for i in range(11, -1, -1):
            month = today - relativedelta(months=i)
            months.append(month)

        return months


    @staticmethod
    def _most_performed_procedures(user, start_date):

        qs = (
            Revenue.objects
            .filter(user=user, date__gte=start_date)
            .values("procedure")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )

        labels = [item["procedure"] for item in qs]
        data = [item["total"] for item in qs]

        return {
            "labels": labels,
            "data": data
        }


    @staticmethod
    def _number_of_procedures(user, start_date):

        months = DashboardService._last_12_months()

        qs = (
            Revenue.objects
            .filter(user=user, date__gte=start_date)
            .annotate(chart_month=TruncMonth("date"))
            .values("chart_month")
            .annotate(total=Count("id"))
            .order_by("chart_month")
        )

        data_map = {
            (item["chart_month"].year, item["chart_month"].month): item["total"]
            for item in qs
        }

        labels = []
        data = []

        for month in months:
            labels.append(f"{MONTH_LABELS[month.month - 1]} {month.year}")
            data.append(data_map.get((month.year, month.month), 0))

        return {
            "labels": labels,
            "data": data
        }


    @staticmethod
    def _monthly_profit(user, start_date):

        revenue = (
            Revenue.objects
            .filter(user=user, date__gte=start_date)
            .annotate(chart_month=TruncMonth("date"))
            .values("chart_month")
            .annotate(total=Sum("value"))
        )

        expense = (
            Expense.objects
            .filter(user=user, date__gte=start_date)
            .annotate(chart_month=TruncMonth("date"))
            .values("chart_month")
            .annotate(total=Sum("value"))
        )

        revenue_map = {
            (r["chart_month"].year, r["chart_month"].month): r["total"]
            for r in revenue
        }
        expense_map = {
            (e["chart_month"].year, e["chart_month"].month): e["total"]
            for e in expense
        }

        months = DashboardService._last_12_months()

        labels = []
        data = []

        for month in months:
            revenue = revenue_map.get((month.year, month.month), 0)
            expense = expense_map.get((month.year, month.month), 0)

            labels.append(f"{MONTH_LABELS[month.month - 1]} {month.year}")
            data.append(revenue - expense)

        return {
            "labels": labels,
            "data": data
        }


    @staticmethod
    def _revenue_vs_expense(user, start_date):

        revenue = (
            Revenue.objects
            .filter(user=user, date__gte=start_date)
            .annotate(chart_month=TruncMonth("date"))
            .values("chart_month")
            .annotate(total=Sum("value"))
        )

        expense = (
            Expense.objects
            .filter(user=user, date__gte=start_date)
            .annotate(chart_month=TruncMonth("date"))
            .values("chart_month")
            .annotate(total=Sum("value"))
        )

        revenue_map = {
            (r["chart_month"].year, r["chart_month"].month): r["total"]
            for r in revenue
        }
        expense_map = {
            (e["chart_month"].year, e["chart_month"].month): e["total"]
            for e in expense
        }

        months = DashboardService._last_12_months()

        labels = []
        revenue_data = []
        expense_data = []

        for month in months:
            labels.append(f"{MONTH_LABELS[month.month - 1]} {month.year}")
            revenue_data.append(revenue_map.get((month.year, month.month), 0))
            expense_data.append(expense_map.get((month.year, month.month), 0))

        return {
            "labels": labels,
            "data": {
                "revenue": revenue_data,
                "expense": expense_data
            }
        }