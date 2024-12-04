import os
import json
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from upfit_gym.models import *

# Command:
# python manage.py import_customers --file upfit_gym/database/customer2024.json

class Command(BaseCommand):
    help = "Import customers from JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help="Path to customers JSON file.",
            default='upfit_gym/database/customer2024.json',
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write(f"Reading data from: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                customers_data = json.load(f)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Error to read JSON: {e}"))
            return

        self.stdout.write(f"Starting import from {len(customers_data)} customers...")

        with transaction.atomic():
            for item in customers_data:
                try:
                    customer, created = Customer.objects.get_or_create(
                        id=item.get('id'),
                        defaults={
                            'name': item['name'],
                            'frequency': item['frequency'],
                            'start': item['start'],
                            'plan': item['plan'],
                            'value': item['value'],
                            'status': item['status'],
                            'notes': item['notes'],
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Customer '{customer.name}' created successfully!"))
                    else:
                        self.stdout.write(f"Customer '{customer.name}' already exists.")
                except IntegrityError as e:
                    self.stdout.write(self.style.ERROR(f"Error to create customer: {e}"))

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))
