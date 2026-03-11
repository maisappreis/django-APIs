from datetime import datetime
from dateutil.relativedelta import relativedelta
from babel.dates import format_date
from django.db.models import Model, Sum
from datetime import timedelta
from django.db.models import Sum
from .models import *

# TODO: Separar utils dos Charts dos utils do MonthClosing
# E separar os utils 'globais' do back, usados por mais de 1 app

# TODO: Fazer APIs apenas para os Charts




def calculate_sum_values(user: User, model: Model, month: int, year: int, date_field: str = 'date', value_field: str = 'value') -> float:
    """
    Calculates the total of the values ​​of a model column for the specified period.

    Args:
        model (Model): The Django model to query.
        month (int): The month to filter the entries for.
        year (int): The year to filter the entries for.
        date_field (str): The name of the date field in the model. Defaults to 'date'.
        value_field (str): The name of the value field in the model. Defaults to 'value'.

    Returns:
        float: The total sum for the specified period. Returns 0 if there are no results.
    """
    total_value = model.objects.filter(
        user=user,
        **{
            f"{date_field}__month": month,
            f"{date_field}__year": year
        }
    ).aggregate(total_value=Sum(value_field))['total_value'] or 0

    return total_value


def calculate_profit(revenue, expenses):
    return revenue - expenses


def calculate_balance(
    bank_value,
    cash_value,
    card_value,
    other_revenue,
    expenses,
    net_profit
):
    bank_value = bank_value or 0
    cash_value = cash_value or 0
    card_value = card_value or 0
    other_revenue = other_revenue or 0
    expenses = expenses or 0
    net_profit = net_profit or 0

    return (bank_value + cash_value + card_value + other_revenue) - (expenses + net_profit)


def perform_calculations(user: User, revenueModel: Model, expenseModel: Model, data: dict):
    '''
    Performs the calculations required to close a specific month.

    Calculates total gross revenue.
    Calculates total net revenue.
    Calculates total expenses.
    Calculates profit.
    Calculates final balance.
    '''
    month = data.get('month')
    year = data.get('year')
    bank_value = data.get('bank_value')
    cash_value = data.get('cash_value')
    card_value = data.get('card_value')
    card_value_next_month = data.get('card_value_next_month')
    expenses = data.get('expenses')
    other_revenue = data.get('other_revenue')

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    gross_revenue = calculate_sum_values(user, revenueModel, month=month, year=year, date_field='date')
    net_revenue = calculate_sum_values(user, revenueModel, month=month, year=year, date_field='date', value_field='net_value')
    expenses = calculate_sum_values(user, expenseModel, month=next_month, year=next_year)
    
    half_expenses = expenses/2
    net_profit = calculate_profit(net_revenue, half_expenses)
    
    card_value_this_month = card_value - card_value_next_month
    balance = calculate_balance(bank_value, cash_value, card_value_this_month, other_revenue, expenses, net_profit)

    data['bank_value'] = bank_value
    data['cash_value'] = cash_value
    data['card_value'] = card_value
    data['card_value_next_month'] = card_value_next_month
    data['gross_revenue'] = gross_revenue
    data['net_revenue'] = net_revenue
    data['expenses'] = expenses
    data['net_profit'] = net_profit
    data['other_revenue'] = expenses/2
    data['balance'] = balance

    return data


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


def update_month_closing(user, month: int, year: int, reference: str):
    """
    Recalculates MonthClosing values for the given user, month and year.
    """

    gross_revenue = (
        Revenue.objects.filter(user=user, date__month=month, date__year=year)
        .aggregate(total=Sum("value"))["total"] or 0
    )

    net_revenue = (
        Revenue.objects.filter(user=user, date__month=month, date__year=year)
        .aggregate(total=Sum("net_value"))["total"] or 0
    )

    expenses = (
        Expense.objects.filter(user=user, date__month=month, date__year=year)
        .aggregate(total=Sum("value"))["total"] or 0
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