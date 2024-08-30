from datetime import datetime
from dateutil.relativedelta import relativedelta
from babel.dates import format_date

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