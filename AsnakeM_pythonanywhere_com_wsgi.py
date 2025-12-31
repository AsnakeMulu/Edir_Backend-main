import sys
import os

path = '/home/AsnakeM/edir_amba'
if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edir_amba.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
