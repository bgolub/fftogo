from datetime import datetime, timedelta

from google.appengine.ext import db

from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase
from django.core.cache import cache

from django_ae_utils.sessions.models import Session

class SessionStore(SessionBase):
    """
    A google appengine datastore based session store. 
    """
        
    def __init__(self, session_key=None):
        '''Constructor for the SessionStore Class.'''
        self._datastore_session = None
        
        if session_key:
            query = db.Query(Session)
            query = query.filter("session_key =", session_key)
            self._datastore_session = query.get()
        
        super(SessionStore, self).__init__(session_key)
    
    def load(self):
        '''Loads session data from the datastore.'''
        session_data = {}
        if self._datastore_session:
            if self._datastore_session.expire_date > datetime.now():
                if self._datastore_session.session_data:
                    session_data = self.decode(self._datastore_session.session_data)
                else:
                    session_data = None
            else:
                self.delete(self._datastore_session.session_key)
            
        return session_data or {}

    def save(self):
        '''Saves the session data to the datastore.'''
        time_till_expire = timedelta(seconds=settings.SESSION_COOKIE_AGE)
        expire_date = datetime.now() + time_till_expire
        
        if self._datastore_session:
            self._datastore_session.session_data = self.encode(self._session)
        else:
            self._datastore_session = Session(session_key=self.session_key, session_data=self.encode(self._session), expire_date=expire_date)
        self._datastore_session.put()
        

    def exists(self, session_key):
        '''Checks to see if the session exists.'''
        exists = False
        used_cache = False
        session = self._get_session(session_key)

        if session:
            # Check that the session is still valid
            if session.expire_date > datetime.now():
                exists = True
            else:
                exists = False
        else:
            exists = False
            
        return exists
        
    def delete(self, session_key):
        '''Destroys the session and removes it from the datastore.'''

        session = self._get_session(session_key)
        
        if session:
            session.delete()
            self._datastore_session = None
            
    def _get_session(self, session_key = None):
        '''Attempts to retreive the cached session and falls back to the stored session if needed.'''
        session = None
        
        # Try to use the cached session
        if self._datastore_session:
            # Make sure that the cached session matches the session key provided
            if session_key is None or self._datastore_session.session_key == session_key:
                session = self._datastore_session
        
        # Fall back to the stored session
        if session is None and session_key is not None:
            query = db.Query(Session)
            query = query.filter("session_key =", session_key)
            session = query.get()
            
        return session
            