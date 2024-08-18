"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os
import django
from django.core.wsgi import get_wsgi_application
# from django.core.management import call_command
# from .utils import is_development

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# if not is_development:
    # django.setup()
    # call_command('makemigrations')
    # call_command('migrate')

application = get_wsgi_application()
app = application