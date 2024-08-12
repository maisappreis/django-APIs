from django.db import models


class Customer(models.Model):
    STATUS_CHOICES = [
        ('Ativo', 'Ativo'),
        ('Inativo', 'Inativo'),
    ]

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
        unique_together = ['name']


class Expense(models.Model):
    PAYMENT_CHOICES = [
        ('À pagar', 'À pagar'),
        ('Pago', 'Pago'),
    ]

    name = models.CharField(max_length=255, null=False, blank=False)
    year = models.IntegerField(null=False, blank=False)
    month = models.CharField(max_length=50, null=False, blank=False)
    due_date = models.DateField(null=False, blank=False)
    value = models.FloatField(null=False, blank=False)
    paid = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='À pagar')
    notes = models.TextField(null=True, blank=True)
    

    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ['name', 'year', 'month']


class Revenue(models.Model):
    PAYMENT_CHOICES = [
        ('À pagar', 'À pagar'),
        ('Link enviado', 'Link enviado'),
        ('Pago', 'Pago'),
    ]

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
        unique_together = ['customer', 'year', 'month']