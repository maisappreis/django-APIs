from dental_clinic.models import Expense
from dateutil.relativedelta import relativedelta
from babel.dates import format_date

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