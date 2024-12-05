import os
import json
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from upfit_gym.models import Expense

# Command:
# python manage.py import_expense --file upfit_gym/database/expense2024.json

class Command(BaseCommand):
    help = "Import expenses from JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help="Path to expenses JSON file.",
            default='upfit_gym/database/expense2024.json',
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
            self.stdout.write(self.style.ERROR(f"Error to read JSON: {e}"))
            return

        self.stdout.write(f"Starting import of {len(expenses_data)} expenses...")

        with transaction.atomic():
            for item in expenses_data:
                try:
                    expense = Expense.objects.create(
                        name=item['name'],
                        year=item['year'],
                        month=item['month'],
                        date=item['date'],
                        installments=item.get('installments', ''),
                        value=item['value'],
                        paid=item['paid'],
                        notes=item.get('notes', ''),
                    )
                    self.stdout.write(self.style.SUCCESS(f"Expense '{expense.name}' created successfully!"))
                except IntegrityError as e:
                    self.stdout.write(self.style.ERROR(f"Error to create expense: {e}"))

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))
