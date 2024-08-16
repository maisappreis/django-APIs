import os

def is_development():
    return os.getenv('DJANGO_PORT', '8000') == '8000'
