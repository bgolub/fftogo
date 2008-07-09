from django import newforms as forms

class IntegerWidget(forms.TextInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs',{}).update({'size': '2'})
        super(IntegerWidget, self).__init__(*args, **kwargs)

class CommentForm(forms.Form):
    body = forms.CharField(label='Comment', widget=forms.Textarea)
    comment = forms.CharField(widget=forms.HiddenInput, required=False)
    entry = forms.CharField(widget=forms.HiddenInput)
    next = forms.CharField(widget=forms.HiddenInput)

class LoginForm(forms.Form):
    nickname = forms.CharField(label='FriendFeed nickname')
    key = forms.CharField(label='Remote Key', widget=forms.PasswordInput)

class SearchForm(forms.Form):
    search = forms.CharField(label='Query')

class SettingsForm(forms.Form):
    fontsize = forms.IntegerField(label='Font size', min_value=1, widget=IntegerWidget)
    num = forms.IntegerField(label='Number of entries', min_value=1, max_value=30, widget=IntegerWidget)
    newwindow = forms.BooleanField(label='Open links in a new window', required=False)
    googlemobileproxy = forms.BooleanField(label='Open links using Google Mobile Proxy', required=False)
    media = forms.BooleanField(label='Display image thumbnails', required=False)
