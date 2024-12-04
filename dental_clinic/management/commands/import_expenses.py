import os
import json
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from dental_clinic.models import Expense

# Command:
# python manage.py import_expenses --file dental_clinic/database/expense2024.json

class Command(BaseCommand):
    help = "Import expenses for dental_clinic from JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help="Path to expenses JSON file.",
            default='dental_clinic/database/expense2024.json',
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write(f"Reading data from: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                expenses_data = json.load(f)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Error reading JSON: {e}"))
            return

        self.stdout.write(f"Starting import of {len(expenses_data)} expenses...")

        with transaction.atomic():
            for item in expenses_data:
                try:
                    expense, created = Expense.objects.get_or_create(
                        id=item.get('id'),
                        defaults={
                            'year': item['year'],
                            'month': item['month'],
                            'name': item['name'],
                            'installments': item['installments'],
                            'date': item['date'],
                            'value': item['value'],
                            'is_paid': item['is_paid'],
                            'notes': item['notes'],
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Expense '{expense.name}' created successfully!"))
                    else:
                        self.stdout.write(f"Expense '{expense.name}' already exists.")
                except IntegrityError as e:
                    self.stdout.write(self.style.ERROR(f"Error creating expense: {e}"))

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))
