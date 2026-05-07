"""
WSGI config for RAOLY BTP project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekouma.settings')

application = get_wsgi_application()
