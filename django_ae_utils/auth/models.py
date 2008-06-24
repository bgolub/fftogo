from datetime import datetime
import re

from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

from django import newforms as forms

from django_ae_utils.auth import utils 



class User(db.Model):
    first_name = db.StringProperty(required=True)
    last_name = db.StringProperty(required=True)
    email = db.EmailProperty(required=True)
    password = db.StringProperty()
    last_login = db.DateTimeProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)
    
    def login(self, email, password, request=None):
        success = False
        if self.authenticate(email=email, password=password):
            self.last_login = datetime.now()
            self.put()
            if request and request.session:
                request.session['user'] = self
            
            success = True
        
        return success
        
    
    # Verifies the user's credentials against the database
    def authenticate(self, email, password):
        success = False
        
        if email and password:
            try:
                (algorithm, stored_hash, salt) = self.password.split('|')

                new_hash = utils.gen_hash(password=password, salt=salt)
                
                if stored_hash == new_hash:
                    success = True
            
            except Exception:
                pass
        
        return success
        
    def set_password(self, password):
        to_store = ''
        
        if password:
            salt = utils.gen_salt()
            hash = utils.gen_hash(password=password, salt=salt)
            algorithm = 'sha1'
            
            to_store = '|'.join((algorithm, hash, salt))
            
            self.password = to_store
        
        return to_store
        
    def __unicode__(self):
        return u'%s %s' % (self.first_name, self.last_name)


class UniqueEmailField(forms.Field):
    def clean (self, value):
        email_re = re.compile(r'[\w\d\.\-\+]+@[\w\d\.\-\+]+\.[\w\d\.\-\+]+')
        if not email_re.match(value):
            raise forms.ValidationError('You must enter a valid email address')
        query = db.Query(User)
        count = query.filter('email = ', value).count()
        
        if count > 0:
            raise forms.ValidationError('%s is already registered.  Please try a different email address.' % value)
            
        return value

class UserForm(djangoforms.ModelForm):
    email = UniqueEmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        exclude = ['last_login', 'created', 'modified']
