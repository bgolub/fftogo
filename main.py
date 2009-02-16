import logging
import os
import sys

# Remove the standard version of Django.
for k in [k for k in sys.modules if k.startswith('django')]:
    del sys.modules[k]

# Import Django from a zipfile if we don't have it on our path.
if "django" not in os.listdir(os.path.abspath(os.path.dirname(__file__))):
    sys.path.insert(0, os.path.abspath('django.zip'))

# Force sys.path to have our own directory first, in case we want to import
# from it.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Google App Engine imports.
from google.appengine.ext.webapp import util

# Custom Django configuration.
from django.conf import settings
settings._target = None
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Import the part of Django we need.
import django.core.handlers.wsgi

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    # Create a Django application for WSGI.
    application = django.core.handlers.wsgi.WSGIHandler()
    # Run the WSGI CGI handler with that application.
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
