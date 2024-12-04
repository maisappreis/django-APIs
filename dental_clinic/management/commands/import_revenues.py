import os
import json
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from dental_clinic.models import Revenue

# Command:
# python manage.py import_revenues --file dental_clinic/database/revenue2024.json

class Command(BaseCommand):
    help = "Import revenues from JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help="Path to revenues JSON file.",
            default='dental_clinic/database/revenue2024.json',
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
            self.stdout.write(self.style.ERROR(f"Error reading JSON: {e}"))
            return

        self.stdout.write(f"Starting import of {len(revenues_data)} revenues...")

        with transaction.atomic():
            for item in revenues_data:
                try:
                    revenue, created = Revenue.objects.get_or_create(
                        id=item.get('id'),
                        defaults={
                            'date': item['date'],
                            'release_date': item.get('release_date'),
                            'name': item['name'],
                            'cpf': item['cpf'],
                            'nf': item['nf'],
                            'procedure': item['procedure'],
                            'payment': item['payment'],
                            'installments': item['installments'],
                            'value': item['value'],
                            'net_value': item['net_value'],
                            'notes': item.get('notes', ''),
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Revenue '{revenue.name}' created successfully!"))
                    else:
                        self.stdout.write(f"Revenue with ID {revenue.id} already exists.")
                except IntegrityError as e:
                    self.stdout.write(self.style.ERROR(f"Error creating revenue: {e}"))

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))
