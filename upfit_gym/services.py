from dateutil.relativedelta import relativedelta
from babel.dates import format_date
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from upfit_gym.models import Customer, Revenue, Expense


class ExpenseService:

    @staticmethod
    def create_expenses(user, validated_data):

        installments = validated_data.get('installments')

        if not installments:
            expense = Expense.objects.create(
                user=user,
                **validated_data
            )
            return [expense]

        return ExpenseService._create_installments(user, validated_data)


    @staticmethod
    def _create_installments(user, data):

        installments = int(data['installments'])
        initial_date = data['date']

        created = []

        for i in range(installments):

            installment_data = data.copy()

            date_obj = initial_date + relativedelta(months=i)

            installment_data['installments'] = f'{i+1}/{installments}'
            installment_data['date'] = date_obj
            installment_data['month'] = format_date(date_obj, 'MMMM', locale='pt_BR').capitalize()
            installment_data['year'] = date_obj.year

            expense = Expense.objects.create(
                user=user,
                **installment_data
            )

            created.append(expense)

        return created
    

MONTH_LABELS = [
    "Jan", "Fev", "Mar", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Set", "Out", "Nov", "Dez"
]

MONTH_NAME_TO_NUMBER = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12,
}


class DashboardService:

    @staticmethod
    def get_charts(user):

        today = timezone.now()
        twelve_months_ago = today - timedelta(days=365)

        return {
            "active_inactive_customers": DashboardService._active_inactive_customers(user, twelve_months_ago),
            "number_of_active_customer_per_month": DashboardService._number_of_active_customer_per_month(user, twelve_months_ago),
            "monthly_profit": DashboardService._monthly_profit(user, twelve_months_ago),
            "revenue_versus_expense": DashboardService._revenue_vs_expense(user, twelve_months_ago),
        }

    # -----------------------------
    # Helpers
    # -----------------------------

    @staticmethod
    def _last_12_months():

        today = timezone.now().replace(day=1)

        return [
            today - relativedelta(months=i)
            for i in range(11, -1, -1)
        ]

    @staticmethod
    def _month_label(month):
        return f"{MONTH_LABELS[month.month - 1]} {month.year}"

    @staticmethod
    def _empty_chart():
        return {"labels": [], "data": []}

    @staticmethod
    def _revenue_expense_maps(user, start_date):

        revenue = (
            Revenue.objects
            .filter(user=user, year__gte=start_date.year)
            .values("year", "month")
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
            (r["year"], MONTH_NAME_TO_NUMBER[r["month"]]): r["total"]
            for r in revenue
        }

        expense_map = {
            (e["chart_month"].year, e["chart_month"].month): e["total"]
            for e in expense
        }

        return revenue_map, expense_map

    # -----------------------------
    # Charts
    # -----------------------------

    @staticmethod
    def _active_inactive_customers(user, start_date):

        customers = (
            Customer.objects
            .filter(user=user, start__gte=start_date)
            .values("status")
            .annotate(total=Count("id"))
        )

        if not customers.exists():
            return DashboardService._empty_chart()

        status_map = {c["status"]: c["total"] for c in customers}

        return {
            "labels": ["Ativos", "Inativos"],
            "data": [
                status_map.get("Ativo", 0),
                status_map.get("Inativo", 0)
            ]
        }

    @staticmethod
    def _number_of_active_customer_per_month(user, start_date):

        months = DashboardService._last_12_months()

        labels = []
        data = []

        for month in months:

            count = (
                Customer.objects
                .filter(
                    user=user,
                    status="Ativo",
                    start__year=month.year,
                    start__month=month.month
                )
                .count()
            )

            labels.append(DashboardService._month_label(month))
            data.append(count)

        if not any(data):
            return DashboardService._empty_chart()

        return {"labels": labels, "data": data}

    @staticmethod
    def _monthly_profit(user, start_date):

        revenue_map, expense_map = DashboardService._revenue_expense_maps(user, start_date)

        months = DashboardService._last_12_months()

        labels = []
        data = []

        for month in months:

            revenue_value = revenue_map.get((month.year, month.month), 0)
            expense_value = expense_map.get((month.year, month.month), 0)

            labels.append(DashboardService._month_label(month))
            data.append(revenue_value - expense_value)

        if not any(data):
            return DashboardService._empty_chart()

        return {"labels": labels, "data": data}

    @staticmethod
    def _revenue_vs_expense(user, start_date):

        revenue_map, expense_map = DashboardService._revenue_expense_maps(user, start_date)

        months = DashboardService._last_12_months()

        labels = []
        revenue_data = []
        expense_data = []

        for month in months:

            labels.append(DashboardService._month_label(month))

            revenue_data.append(
                revenue_map.get((month.year, month.month), 0)
            )

            expense_data.append(
                expense_map.get((month.year, month.month), 0)
            )

        if not any(revenue_data) and not any(expense_data):
            return {
                "labels": [],
                "data": {"revenue": [], "expense": []}
            }

        return {
            "labels": labels,
            "data": {
                "revenue": revenue_data,
                "expense": expense_data
            }
        }