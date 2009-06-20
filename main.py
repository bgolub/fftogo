import logging
import os
import sys

# Use Django 1.0
from google.appengine.dist import use_library
use_library("django", "1.0")

# Google App Engine imports.
from google.appengine.ext.webapp import util

# Custom Django configuration.
from django.conf import settings
settings._target = None
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Import the part of Django we need.
import django.core.handlers.wsgi

def main():
    logging.getLogger().setLevel(logging.ERROR)
    # Create a Django application for WSGI.
    application = django.core.handlers.wsgi.WSGIHandler()
    # Run the WSGI CGI handler with that application.
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
