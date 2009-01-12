from django import template
from google.appengine.api import memcache

register = template.Library()

@register.filter
def filter_media(value):
    return value[:3]

@register.filter
def filter_thumbnails(value):
    return value[:1]

@register.filter
def summary(value):
    services = {
        'dailymotion': {
            'favorite': 'favorites',
        },
        'digg': {
            'comment': 'comments',
        },
        'facebook': {
            'note': 'notes',
            'post': 'posts',
        },
        'flickr': {
            'favorite': 'favorites',
        },
        'hatena': {
            'bookmark': 'bookmarks',
            'photo': 'photos',
            'post': 'posts',
        },
        'meneame': {
            'comment': 'comments',
        },
        'netflix': {
            'queue': 'queue',
            'instant': 'instant queue',
        },
        'netvibes': 'starred',
        'pandora': {
            'artist': 'artist',
        },
        'reddit': {
            'comment': 'comments',
        },
        'vimeo': {
            'like': 'favorites',
        },
        'wakoopa': {
            'review': 'reviews',
        },
        'youtube': {
            'favorite': 'favorites',
        },
        'zooomr': {
            'favorite': 'favorites',
        },
    }
    service = value['service']
    if service['id'] == 'internal':
        return ''
    entryType = service.get('entryType', None)
    type = services.get(service['id'], {}).get(entryType)
    if type:
        return ' '.join([service['name'], type])
    return service['name']
 
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
    services = (
        'googletalk',
        'identica',
        'plurk',
        'twitter',
    )
    if value['service']['id'] in services:
        return True 
    if value['service']['id'] == 'jaiku':
        return value['service']['profileUrl'].lower() in value['link'].lower()
    if value['service']['id'] == 'facebook':
        return value['service'].get('entryType', None) != 'post'
    if value['service']['id'] == 'feed':
        return value['service'].get('entryType', None) != 'post'
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
def shorten_comments(value, arg):
    if len(value) > 4 and len(arg) > 1:
        return value[:1] + [{'permalink': True, 'num': len(value) - 3},] + value[-2:]
    return value

@register.filter
def shorten_likes(value, arg):
    if len(value) > 4 and len(arg) > 1:
        return value[:3] + [{'permalink': True, 'num': len(value) - 3},]
    return value

@register.filter
def twitterize(value):
    import re
    for user in re.findall(r'@(\w+)', value):
        value = value.replace('@%s' % user, '@<a href="http://twitter.com/%s">%s</a>' % (user, user))
    return value
