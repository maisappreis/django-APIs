from django.db import models
# from django.contrib.auth.models import User

# Real models used by authenticated users.


class Revenue(models.Model):
    # user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='revenues')
    date = models.DateField(null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    cpf = models.CharField(max_length=14, null=False, blank=True)
    nf = models.BooleanField(default=False, null=False, blank=False)
    procedure = models.CharField(max_length=255, null=False, blank=False)
    payment = models.CharField(max_length=255, null=False, blank=False)
    installments = models.IntegerField(null=False, blank=False)
    value = models.FloatField(null=False, blank=False)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ['date', 'name', 'procedure', 'value']


class Expense(models.Model):
    # user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    year = models.IntegerField(null=False, blank=False)
    month = models.CharField(max_length=50, null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    installments = models.CharField(max_length=50, null=False, blank=True)
    date = models.DateField(null=False, blank=False)
    value = models.FloatField(null=False, blank=False)
    is_paid = models.BooleanField(default=False, null=False, blank=False)
    notes = models.TextField(null=True, blank=True)
   
    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ['name', 'year', 'month', 'value']


class Agenda(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    date = models.DateField(null=False, blank=False)
    time = models.CharField(max_length=10, null=False, blank=False)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ['name', 'date', 'time']


# Test models used by unauthenticated users test application, like a portfolio.


class RevenueTest(models.Model):
    date = models.DateField(null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    cpf = models.CharField(max_length=14, null=False, blank=True)
    nf = models.BooleanField(default=False, null=False, blank=False)
    procedure = models.CharField(max_length=255, null=False, blank=False)
    payment = models.CharField(max_length=255, null=False, blank=False)
    installments = models.IntegerField(null=False, blank=False)
    value = models.FloatField(null=False, blank=False)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ['date', 'name', 'procedure', 'value']


class ExpenseTest(models.Model):
    year = models.IntegerField(null=False, blank=False)
    month = models.CharField(max_length=50, null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    installments = models.CharField(max_length=50, null=False, blank=True)
    date = models.DateField(null=False, blank=False)
    value = models.FloatField(null=False, blank=False)
    is_paid = models.BooleanField(default=False, null=False, blank=False)
    notes = models.TextField(null=True, blank=True)
   
    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ['name', 'year', 'month', 'value']


class AgendaTest(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    date = models.DateField(null=False, blank=False)
    time = models.CharField(max_length=10, null=False, blank=False)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ['name', 'date', 'time']
