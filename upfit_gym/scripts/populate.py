import os
import django
import sqlite3
from datetime import datetime
from django.conf import settings
from django.db.models import Count
import logging
from django.utils import timezone
from django.http import JsonResponse
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from models import *


directory = os.path.join(settings.BASE_DIR)
file = os.path.join(directory, 'db.json')


conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()


with open(file, 'r', encoding='utf-8') as db_json:
    db_data = json.load(db_json)


# for item in db_data['customers']:
#     print(item['name'])

#     customer = Customer(
#         name = item['name'],
#         frequency = item['frequency'],
#         start = item['start'],
#         plan = item['plan'],
#         value = item['value'],
#         status = item['status'],
#         notes = item['notes'] 
#     )
#     customer.save()

# conn.commit()
# conn.close()
    

# for item in db_data['revenue']:
#     customer_id = item['customer_id']
#     print(customer_id)

#     try:
#         customer = Customer.objects.get(id=customer_id)

#         revenue = Revenue(
#             customer = customer,
#             year = item['year'],
#             month = item['month'],
#             payment_day = item['payment_day'],
#             value = item['value'],
#             paid = item['paid'],
#             notes = item['notes'],
#         )
#         # revenue.save()
#     except Customer.DoesNotExist:
#         print(f'Customer does not exist! {item.id}', item['id'])
#         customer = None


for item in db_data['revenue']:
    customer_id = item['customer_id']
    month_json = item['month']
    print(customer_id)

    if month_json == "Dezembro":
        try:
            customer = Customer.objects.get(id=customer_id)

            revenue = Revenue(
                customer = customer,
                year = 2024,
                month = "Janeiro",
                payment_day = item['payment_day'],
                value = item['value'],
                paid = "À pagar",
                notes = item['notes'],
            )
            # revenue.save()
        except Customer.DoesNotExist:
            print(f'Customer does not exist! {item.id}', item['id'])
            customer = None


conn.commit()
conn.close()
    

