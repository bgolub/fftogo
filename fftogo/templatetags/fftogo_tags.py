from django import template

register = template.Library()
 
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
def liked(value, arg):
    return value in [like['user']['nickname'] for like in arg['likes']]

@register.filter
def likeable(value, arg):
    if value['anonymous']:
        return True
    return value['user']['nickname'] != arg
