from django.db import models
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint


class Revenue(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(null=False, blank=False)
    release_date = models.DateField(null=True, blank=True, default=None)
    name = models.CharField(max_length=255, null=False, blank=False)
    cpf = models.CharField(max_length=14, null=False, blank=True)
    nf = models.BooleanField(default=False, null=False, blank=False)
    procedure = models.CharField(max_length=255, null=False, blank=False)
    payment = models.CharField(max_length=255, null=False, blank=False)
    installments = models.IntegerField(null=True, blank=True)
    value = models.FloatField(null=False, blank=False)
    net_value = models.FloatField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['user', 'date', 'name', 'procedure', 'value'],
                name='unique_revenue_per_user'
            )
        ]


class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    year = models.IntegerField(null=False, blank=False)
    month = models.CharField(max_length=50, null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    installments = models.CharField(max_length=50, null=True, blank=True)
    date = models.DateField(null=False, blank=False)
    value = models.FloatField(null=False, blank=False)
    is_paid = models.BooleanField(default=False, null=False, blank=False)
    notes = models.TextField(null=True, blank=True)
   
    def __str__(self):
        return self.name
    
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['user', 'name', 'year', 'month', 'value'],
                name='unique_expense_per_user'
            )
        ]


class Appointment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=False, blank=False)
    date = models.DateField(null=False, blank=False)
    time = models.CharField(max_length=10, null=False, blank=False)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['user', 'name', 'date', 'time'],
                name='unique_appointment_per_user'
            )
        ]


class MonthClosing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    reference = models.CharField(max_length=55, null=False, blank=False)
    month = models.IntegerField(null=False, blank=False)
    year = models.IntegerField(null=False, blank=False)

    gross_revenue =  models.FloatField(null=False, blank=False)
    net_revenue =  models.FloatField(null=False, blank=False)
    expenses =  models.FloatField(null=False, blank=False)
    net_profit =  models.FloatField(null=False, blank=False)

    bank_value =  models.FloatField(null=True, blank=True)
    cash_value =  models.FloatField(null=True, blank=True)
    card_value =  models.FloatField(null=True, blank=True)
    card_value_next_month =  models.FloatField(default=0, null=True, blank=True)

    other_revenue =  models.FloatField(null=True, blank=True)
    balance =  models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.reference
    
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['user', 'reference', 'month', 'year'],
                name='unique_month_closing_per_user'
            )
        ]