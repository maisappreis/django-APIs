from datetime import date
from uuid import uuid4

from django.contrib.auth import get_user_model

from upfit_gym.models import Customer, Expense, Revenue


User = get_user_model()


def create_user(username=None):
    return User.objects.create_user(
        username=username or f"upfit-user-{uuid4()}",
        password="password",
    )


def create_customer(user=None, **kwargs):
    user = user or create_user()
    defaults = {
        "name": f"Customer {uuid4()}",
        "frequency": "2x",
        "start": date(2026, 6, 15),
        "plan": "Mensal",
        "value": 200,
        "status": "Ativo",
        "notes": "test",
    }
    defaults.update(kwargs)
    return Customer.objects.create(user=user, **defaults)


def create_revenue(user=None, customer=None, **kwargs):
    user = user or create_user()
    customer = customer or create_customer(user=user)
    defaults = {
        "customer": customer,
        "year": 2026,
        "month": "Junho",
        "payment_day": 10,
        "value": 200,
        "paid": "Pago",
        "notes": "test",
    }
    defaults.update(kwargs)
    return Revenue.objects.create(user=user, **defaults)


def create_expense(user=None, **kwargs):
    user = user or create_user()
    defaults = {
        "name": f"Expense {uuid4()}",
        "year": 2026,
        "month": "Junho",
        "date": date(2026, 6, 15),
        "installments": "",
        "value": 100,
        "paid": "A pagar",
        "notes": "test",
    }
    defaults.update(kwargs)
    return Expense.objects.create(user=user, **defaults)
