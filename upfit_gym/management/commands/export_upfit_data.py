import os
import json
from datetime import date, datetime
from django.core.management.base import BaseCommand
from upfit_gym.models import Customer, Revenue, Expense


def custom_serializer(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class Command(BaseCommand):
    help = 'Exporta dados do banco de dados para um arquivo JSON'

    def handle(self, *args, **kwargs):
        data = list(Expense.objects.all().values())
        
        directory = 'upfit_gym/database'
        json_file_path = os.path.join(directory, 'expense2024.json')
        
        os.makedirs(directory, exist_ok=True)
        
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4, default=custom_serializer)
        
        self.stdout.write(self.style.SUCCESS(f'Dados exportados para {json_file_path}'))
