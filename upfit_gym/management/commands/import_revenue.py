import os
import json
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from upfit_gym.models import Revenue, Customer

# Command:
# python manage.py import_revenue --file upfit_gym/database/revenue2024.json

class Command(BaseCommand):
    help = "Import revenues from JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help="Path to revenues JSON file.",
            default='upfit_gym/database/revenue2024.json',
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write(f"Reading data from: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                revenues_data = json.load(f)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Error to read JSON: {e}"))
            return

        self.stdout.write(f"Starting import of {len(revenues_data)} revenues...")

        with transaction.atomic():
            for item in revenues_data:
                try:
                    customer_id = item.get('customer_id')
                    try:
                        customer = Customer.objects.get(id=customer_id)
                    except Customer.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f"Customer with ID {customer_id} does not exist. Skipping entry."))
                        continue

                    revenue, created = Revenue.objects.get_or_create(
                        id=item.get('id'),
                        defaults={
                            'customer': customer,
                            'year': item['year'],
                            'month': item['month'],
                            'payment_day': item['payment_day'],
                            'value': item['value'],
                            'paid': item['paid'],
                            'notes': item['notes'],
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Revenue for Customer ID {customer_id} created successfully!"))
                    else:
                        self.stdout.write(f"Revenue with ID {revenue.id} already exists.")
                except IntegrityError as e:
                    self.stdout.write(self.style.ERROR(f"Error to create revenue: {e}"))

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))
