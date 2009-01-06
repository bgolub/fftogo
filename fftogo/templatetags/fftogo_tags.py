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
        'backtype': 'commented on',
        'brightkite': 'checked in',
        'dailymotion': {
            'favorite': 'favorited',
            'publish': 'published',
        },
        'delicious': 'bookmarked',
        'digg': {
            'comment': 'commented on',
            'digg': 'dugg',
        },
        'diigo': 'bookmarked',
        'disqus': 'commented',
        'facebook': {
            'note': 'posted',
            'post': 'shared',
            'status': 'posted',
        },
        'feed': {
            'post': 'posted',
            'status': 'posted',
        },
        'flickr': {
            'favorite': 'favorited',
            'publish': 'published',
        },
        'fotolog': 'published',
        'goodreads': 'read',
        'googletalk': 'had a new status message',
        'googlereader': 'shared',
        'googleshared': 'shared',
        'hatena': {
            'bookmark': 'bookmarked',
            'photo': 'published',
            'post': 'posted',
        },
        'internal': {
            'link': 'posted a link',
            'message': 'posted a message',
        },
        'intensedebate': 'commented',
        'joost': 'watched',
        'lastfm': 'loved',
        'librarything': 'added',
        'linkedin': {
            'leftjob': 'left their job',
            'newjob': 'got a new job',
        },
        'magnolia': 'bookmarked',
        'meneame': {
            'like': 'liked',
            'comment': 'commented on',
        },
        'misterwong': 'bookmarked',
        'mixx': 'submitted',
        'netflix': {
            'queue': 'added to their queue',
            'instant': 'added to their instant queue',
        },
        'netvibes': 'starred',
        'pandora': {
            'artist': 'bookmarked the artist',
            'song': 'bookmarked the song',
        },
        'photobucket': 'published',
        'picasa': 'published',
        'polyvore': 'created',
        'reddit': {
            'comment': 'commented on',
            'like': 'liked',
        },
        'smotri': 'published',
        'smugmug': 'published',
        'stumbleupon': 'stumbled upon',
        'tipjoy': 'tipped',
        'upcoming': 'added',
        'vimeo': {
            'like': 'liked',
            'publish': 'published',
        },
        'wakoopa': {
            'review': 'reviewed',
            'use': 'started using',
        },
        'yelp': 'reviewed',
        'youtube': {
            'favorite': 'favorited',
            'publish': 'published',
        },
        'zooomr': {
            'favorite': 'favorited',
            'publish': 'published',
        },
    }
    service = value['service']
    type = service.get('entryType', None)
    try:
        if type:
            return services.get(service['id'], {}).get(type, 'posted')
        return services.get(service['id'], 'posted')
    except:
        return 'posted'
 
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
