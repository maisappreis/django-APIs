import os
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from upfit_gym.models import Customer

# Command
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
            self.stdout.write(self.style.ERROR(f"Error reading JSON: {e}"))
            return

        self.stdout.write(f"Starting import of {len(customers_data)} customers...")

        id_mapping = {}

        with transaction.atomic():
            for item in customers_data:
                try:
                    customer = Customer.objects.create(
                        name=item['name'],
                        frequency=item['frequency'],
                        start=item['start'],
                        plan=item['plan'],
                        value=item['value'],
                        status=item['status'],
                        notes=item['notes'],
                    )
                    # Map old ID to new ID
                    id_mapping[item['id']] = customer.id
                    self.stdout.write(self.style.SUCCESS(f"Customer '{customer.name}' created with ID {customer.id}."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error creating customer: {e}"))

        # Save the mapping to a file
        mapping_file = "upfit_gym/database/customer_id_mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(id_mapping, f, indent=4)
        self.stdout.write(self.style.SUCCESS(f"ID mapping saved to {mapping_file}."))

        self.stdout.write(self.style.SUCCESS("Customer import completed successfully."))
