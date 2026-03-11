from datetime import datetime
from django.db.models import Model, Sum
from datetime import timedelta
from django.db.models import Sum
from .models import *

# TODO: Separar utils dos Charts dos utils do MonthClosing
# E separar os utils 'globais' do back, usados por mais de 1 app

# TODO: Fazer APIs apenas para os Charts


def calculate_profit(revenue, expenses):
    return revenue - expenses


month_names = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]


def gross_profit_of_the_last_12_months(revenueModel: Model, expenseModel: Model, user: User):
    """
    Returns a list of monthly profits for the last 12 months.

    Example response: {
        "profit": [1200.50, 850.00, -300.00, ...],
        "labels": ["Janeiro", "Fevereiro", "Março", ...]
    }
    """
    twelve_months_ago = datetime.now() - timedelta(days=365)
    monthly_profit = {}

    # Receita líquida por mês
    revenues = revenueModel.objects.filter(user=user, date__gte=twelve_months_ago).values('date__year', 'date__month').annotate(
        total_revenue=Sum('value')
    )

    # Despesas por mês
    expenses = expenseModel.objects.filter(user=user, date__gte=twelve_months_ago).values('date__year', 'date__month').annotate(
        total_expenses=Sum('value')
    )

    # Popula receitas
    for revenue in revenues:
        key = (revenue['date__year'], revenue['date__month'])
        monthly_profit[key] = {'revenue': revenue['total_revenue'], 'expenses': 0}

    # Popula despesas
    for expense in expenses:
        key = (expense['date__year'], expense['date__month'])
        if key in monthly_profit:
            monthly_profit[key]['expenses'] = expense['total_expenses']
        else:
            monthly_profit[key] = {'revenue': 0, 'expenses': expense['total_expenses']}

    # Organiza lucros e labels
    profit_data = []
    labels = []

    for i in range(12):
        target_date = datetime.now() - timedelta(days=30 * i)
        key = (target_date.year, target_date.month)
        data = monthly_profit.get(key, {'revenue': 0, 'expenses': 0})
        profit = calculate_profit(data['revenue'], data['expenses'])
        profit_data.append(profit)
        labels.append(month_names[target_date.month - 1])

    profit_data.reverse()
    labels.reverse()

    return profit_data, labels