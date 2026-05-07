"""
ASGI config for RAOLY BTP project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekouma.settings')

application = get_asgi_application()
