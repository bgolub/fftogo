from django import template
from google.appengine.api import memcache

register = template.Library()

@register.filter
def can_edit(value):
    key = 'comment_%s' % value['id']
    return memcache.get(key)
 
@register.filter
def gmpize(value, arg=None):
    if arg:
        if not 'fftogo.com' in value:
            value = 'http://www.google.com/gwt/n?u=%s' % value
        return value
    from BeautifulSoup import BeautifulSoup
    soup = BeautifulSoup(value)
    for a in soup.findAll('a'):
        if not 'fftogo.com' in a['href']:
            a['href'] = 'http://www.google.com/gwt/n?u=%s' % a['href']
    return soup

@register.filter
def is_admin(value, arg):
    return value in [administrator['nickname'] for administrator in arg['administrators']]

@register.filter
def is_message(value):
    if value['service']['id'] == 'googletalk':
        return True 
    if value['service']['id'] == 'jaiku':
        return value['service']['profileUrl'].lower() in value['link'].lower()
    return value['link'] == 'http://friendfeed.com/e/%s' % value['id']

@register.filter
def likeable(value, arg):
    if value['anonymous']:
        return True
    return value['user']['nickname'] != arg

@register.filter
def liked(value, arg):
    return value in [like['user']['nickname'] for like in arg['likes']]

@register.filter
def twitterize(value):
    import re
    for user in re.findall(r'@(\w+)', value):
        value = value.replace('@%s' % user, '@<a href="http://twitter.com/%s">%s</a>' % (user, user))
    return value
