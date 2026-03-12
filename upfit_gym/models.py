from django.db import models
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint


class Customer(models.Model):
    STATUS_CHOICES = [
        ('Ativo', 'Ativo'),
        ('Inativo', 'Inativo'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="upfit_customer")
    name = models.CharField(max_length=255, null=False, blank=False)
    frequency = models.CharField(max_length=2, null=False, blank=False)
    start = models.DateField(null=False, blank=False)
    plan = models.CharField(max_length=255, null=False, blank=False)
    value = models.FloatField(null=False, blank=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Ativo')
    notes = models.TextField(null=True, blank=True)


    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['user', 'name'],
                name='unique_customer_per_user_upfit'
            )
        ]


class Revenue(models.Model):
    PAYMENT_CHOICES = [
        ('À pagar', 'À pagar'),
        ('Link enviado', 'Link enviado'),
        ('Pago', 'Pago'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="upfit_revenue")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=False)
    year = models.IntegerField(null=False, blank=False)
    month = models.CharField(max_length=50, null=False, blank=False)
    payment_day = models.IntegerField(null=False, blank=False)
    value = models.FloatField(null=False, blank=False)
    paid = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='À pagar')
    notes = models.TextField(null=True, blank=True)


    def __str__(self):
        return self.customer
    
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['user', 'customer', 'year', 'month', 'value'],
                name='unique_revenue_per_user_per_month_year'
            )
        ]


class Expense(models.Model):
    PAYMENT_CHOICES = [
        ('À pagar', 'À pagar'),
        ('Pago', 'Pago'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="upfit_expense")
    name = models.CharField(max_length=255, null=False, blank=False)
    year = models.IntegerField(null=False, blank=False)
    month = models.CharField(max_length=50, null=False, blank=False)
    date = models.DateField(null=False, blank=False)
    installments = models.CharField(max_length=50, null=False, blank=True)
    value = models.FloatField(null=False, blank=False)
    paid = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='À pagar')
    notes = models.TextField(null=True, blank=True)
    

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['user', 'name', 'year', 'month', 'value'],
                name='unique_expense_per_user_per_month_year'
            )
        ]