from datetime import datetime
from dateutil.relativedelta import relativedelta
from babel.dates import format_date
from django.db.models import Model, Sum

def createInstallments(serializer_class, perform_create, installments, data):
    installments = int(installments)
    initial_date = datetime.strptime(data['date'], "%Y-%m-%d")
    created_objects = []

    for i in range(installments):
        installment_data = data.copy()
        installment_data['installments'] = f"{i+1}/{installments}"
        date_obj = initial_date + relativedelta(months=i)
        installment_data['date'] = date_obj.strftime("%Y-%m-%d")
        month_name = format_date(date_obj, format='MMMM', locale='pt_BR')
        installment_data['month'] = month_name.capitalize()
        installment_data['year'] = date_obj.year

        serializer = serializer_class(data=installment_data)
        serializer.is_valid(raise_exception=True)
        perform_create(serializer)
        created_objects.append(serializer.data)

    return serializer, created_objects


def calculate_sum_values(model: Model, month: int, year: int, date_field: str = 'date', value_field: str = 'value') -> float:
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
        **{
            f"{date_field}__month": month,
            f"{date_field}__year": year
        }
    ).aggregate(total_value=Sum(value_field))['total_value'] or 0

    return total_value


def calculate_profit(net_revenue, expenses):
    return net_revenue - expenses


def calculate_balance(bank_value, cash_value, card_value, other_revenue, expenses, profit):
    return (bank_value + cash_value + card_value + other_revenue) - (expenses + profit)


def perform_calculations(revenueModel: Model, expenseModel: Model, data: dict):
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

    gross_revenue = calculate_sum_values(revenueModel, month=month, year=year, date_field='date')
    net_revenue = calculate_sum_values(revenueModel, month=month, year=year, date_field='date', value_field='net_value')
    expenses = calculate_sum_values(expenseModel, month=next_month, year=next_year)
    
    half_expenses = expenses/2
    profit = calculate_profit(net_revenue, half_expenses)
    
    card_value_this_month = card_value - card_value_next_month
    balance = calculate_balance(bank_value, cash_value, card_value_this_month, other_revenue, expenses, profit)

    data['bank_value'] = bank_value
    data['cash_value'] = cash_value
    data['card_value'] = card_value
    data['card_value_next_month'] = card_value_next_month
    data['gross_revenue'] = gross_revenue
    data['net_revenue'] = net_revenue
    data['expenses'] = expenses
    data['profit'] = profit
    data['other_revenue'] = expenses/2
    data['balance'] = balance

    return data