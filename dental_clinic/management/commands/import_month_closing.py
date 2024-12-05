import os
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from dental_clinic.models import MonthClosing

# Command:
# python manage.py import_month_closing --file dental_clinic/database/monthclosing2024.json

class Command(BaseCommand):
    help = "Import month closing data for dental_clinic from JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help="Path to month closing JSON file.",
            default='dental_clinic/database/monthclosing2024.json',
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write(f"Reading data from: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                month_closing_data = json.load(f)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Error reading JSON: {e}"))
            return

        self.stdout.write(f"Starting import of {len(month_closing_data)} month closing records...")

        with transaction.atomic():
            for item in month_closing_data:
                try:
                    MonthClosing.objects.create(
                        reference=item['reference'],
                        month=item['month'],
                        year=item['year'],
                        bank_value=item['bank_value'],
                        cash_value=item['cash_value'],
                        card_value=item['card_value'],
                        card_value_next_month=item['card_value_next_month'],
                        gross_revenue=item['gross_revenue'],
                        net_revenue=item['net_revenue'],
                        expenses=item['expenses'],
                        profit=item['profit'],
                        other_revenue=item['other_revenue'],
                        balance=item['balance'],
                    )
                    self.stdout.write(self.style.SUCCESS(f"MonthClosing '{item['reference']}' created successfully!"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error creating MonthClosing: {e}"))

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))
