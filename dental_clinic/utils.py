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