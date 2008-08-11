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
def find_verb(value):
    services = {
        'amazon': 'added',
        'brightkite': 'checked in',
        'delicious': 'bookmarked',
        'digg': 'dugg',
        'diigo': 'bookmarked',
        'disqus': 'commented',
        'flickr': 'published/favorited',
        'goodreads': 'read',
        'googletalk': 'had a new status message',
        'googlereader': 'shared',
        'googleshared': 'shared',
        'intensedebate': 'commented',
        'lastfm': 'loved',
        'librarything': 'added',
        'linkedin': 'updated their job title',
        'magnolia': 'bookmarked',
        'misterwong': 'bookmarked',
        'mixx': 'submitted',
        'netflix': 'added',
        'netvibes': 'starred',
        'pandora': 'bookmarked',
        'picasa': 'published',
        'polyvore': 'created',
        'reddit': 'liked',
        'smugmug': 'published',
        'stumbleupon': 'stumbled upon',
        'tipjoy': 'tipped',
        'upcoming': 'added',
        'vimeo': 'published/liked',
        'yelp': 'reviewed',
        'youtube': 'published/favorited',
        'zooomr': 'published',
    }
    return services.get(value['service']['id'], 'posted')
 
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
    if len(value) > 6 and len(arg) > 1:
        return value[:2] + [{'permalink': True, 'num': len(value) - 5},] + value[-3:]
    return value

@register.filter
def shorten_likes(value, arg):
    if len(value) > 5 and len(arg) > 1:
        return value[:4] + [{'permalink': True, 'num': len(value) - 4},]
    return value

@register.filter
def twitterize(value):
    import re
    for user in re.findall(r'@(\w+)', value):
        value = value.replace('@%s' % user, '@<a href="http://twitter.com/%s">%s</a>' % (user, user))
    return value
