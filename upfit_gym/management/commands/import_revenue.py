import os
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from upfit_gym.models import Revenue, Customer

# Command
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
        mapping_file = "upfit_gym/database/customer_id_mapping.json"
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"Revenue file not found: {file_path}"))
            return
        
        if not os.path.exists(mapping_file):
            self.stdout.write(self.style.ERROR(f"Mapping file not found: {mapping_file}"))
            return

        # Load the mapping file
        with open(mapping_file, 'r', encoding='utf-8') as f:
            id_mapping = json.load(f)

        self.stdout.write(f"Reading data from: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                revenues_data = json.load(f)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Error reading JSON: {e}"))
            return

        self.stdout.write(f"Starting import of {len(revenues_data)} revenues...")

        with transaction.atomic():
            for item in revenues_data:
                try:
                    # Map old customer ID to new customer ID
                    old_customer_id = item.get('customer_id')
                    new_customer_id = id_mapping.get(str(old_customer_id))

                    if not new_customer_id:
                        self.stdout.write(self.style.ERROR(f"Customer with old ID {old_customer_id} not found in mapping. Skipping entry."))
                        continue

                    customer = Customer.objects.get(id=new_customer_id)

                    Revenue.objects.create(
                        customer=customer,
                        year=item['year'],
                        month=item['month'],
                        payment_day=item['payment_day'],
                        value=item['value'],
                        paid=item['paid'],
                        notes=item['notes'],
                    )
                    self.stdout.write(self.style.SUCCESS(f"Revenue for Customer ID {old_customer_id} created successfully!"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error creating revenue: {e}"))

        self.stdout.write(self.style.SUCCESS("Revenue import completed successfully."))
