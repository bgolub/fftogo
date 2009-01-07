# Python Imports

# Google AppEngine Imports
from google.appengine.ext import db

# Django Imports
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django import newforms as forms

# ae_utils Imports
from django_ae_utils.auth.models import User, UserForm

def register(request, template=None, next_url=None):
    action_url = '.'

    try:
        if request.REQUEST['next_url']:
            next_url = request.REQUEST['next_url']
            action_url = '%s?next_url=%s' % (action_url, next_url)
    except:
        pass
        
    if 'user' in request.session.keys():
        # Redirect the user to the next desired page or to the site's root
        if next_url:
            return HttpResponseRedirect(next_url)
        else:
            return HttpResponseRedirect('/')
            
    # Handle a submitted form
    if request.method == "POST":
        form = UserForm(request.POST)
        
        # If all of the user's submission validates, they are registered.
        # Otherwise Django's forms library and the template will provide the
        # user with feedback.
        if form.is_valid():
            # Load the form data into a User object
            user = form.save(commit=False)
            clear_password = user.password
            
            # Set the users hashed password and save the user
            user.set_password(clear_password)
            user.put()
            
            # Log the user in
            user.login(email=user.email, password=clear_password, request=request)
            
            # Redirect the user to the next desired page or to the site's root
            if next_url:
                return HttpResponseRedirect(next_url)
            else:
                return HttpResponseRedirect('/')
                
    # Handle a request for the page
    else:
        form = UserForm()
        
    c = RequestContext(request, {
        'form':form,
        'action_url':action_url,
    })
    
    if template is None:
        template = 'register.html'
    
    return render_to_response(template, c)
    
    
class LoginForm(forms.Form):
    email = forms.EmailField(max_length=100)
    password = forms.CharField(max_length=100, widget=forms.PasswordInput)
    
def login(request, template=None, next_url=None):
    feedback = ''
    action_url = '.'

    if 'user' in request.session.keys():
        # Redirect the user to the next desired page or to the site's root
        if next_url:
            return HttpResponseRedirect(next_url)
        else:
            return HttpResponseRedirect('/')
            
    try:
        if request.REQUEST['next_url']:
            next_url = request.REQUEST['next_url']
            action_url = '%s?next_url=%s' % (action_url, next_url)
    except:
        pass
    
    if request.method == "POST":
        form = LoginForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            query = db.Query(User)
            user = query.filter('email =', email).get()
            
            if user:
                success = user.login(email=email, password=password, request=request)
                
                if success:
                    # Redirect the user to the next desired page or to the site's root
                    if next_url is not None:
                        return HttpResponseRedirect(next_url)
                    else:
                        return HttpResponseRedirect('/')
                else:
                    feedback = "Bad username and password.  Please try again."    
            else:
                feedback = "Bad username and password.  Please try again."
    else:
        form = LoginForm()    
        
    c = RequestContext(request, {
        'form':form,
        'feedback':feedback,
        'action_url':action_url,
    })
    
    if template is None:
        template = 'login.html'
    
    return render_to_response(template, c)
    
def logout(request, next_url=None):
    try:
        request.GET['next_url']
        next_url = request.GET['next_url']
    except Exception:
        pass
    
    if 'user' in request.session.keys():
        del request.session['user']
    
    if next_url:
        return HttpResponseRedirect(next_url)
    else:
        return HttpResponseRedirect('/')