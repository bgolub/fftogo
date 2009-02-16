import logging
import friendfeed
import urllib
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import feedgenerator
from fftogo.forms import CommentForm, LoginForm, SearchForm, SettingsForm
from google.appengine.api import memcache

PUBLIC_CACHE_TIME = settings.PUBLIC_CACHE_TIME
FONT_SIZE = settings.FONT_SIZE
GMP = settings.GMP
MEDIA = settings.MEDIA
NEW_WINDOW = settings.NEW_WINDOW
NUM = settings.NUM
VIA = settings.VIA
NO_MEDIA = settings.NO_MEDIA

def querydict_to_dict(arguments):
    supported = set(['service', 'num', 'start'])
    kwargs = {}
    for name in arguments:
        if name not in supported:
            continue
        value = arguments.get(name)
        if value:
            kwargs[str(name)] = value
    return kwargs

def get_integer_argument(request, name, default):
    try:
        return int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default

def atom(entries):
    '''Build and return an Atom feed.

    entries is a list of entries straight from the FriendFeed API.
    '''
    f = feedgenerator.Atom1Feed(
        title = 'FF To Go',
        link = 'http://www.fftogo.com',
        description = 'FF To Go',
        language = 'en',
    )
    for entry in entries:
        f.add_item(
            title = entry['title'],
            link = entry['link'],
            description = '<a href="http://www.fftogo.com/e/%s">View in fftogo</a>' % entry['id'],
            author_name = entry['user']['name'],
            pubdate = entry['updated'],
        )
    return HttpResponse(f.writeString('utf-8'))

def error(request, data):
    if data['statusCode'] == 401 and 'nickname' in request.session:
        del request.session['nickname']
        del request.session['key']
    return render_to_response('error.html', data, context_instance=RequestContext(request))

def comment_delete(request, entry, comment):
    '''Delete a comment.

    Authentication is required.

    entry is the entry id.
    comment is the comment id.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.delete_comment(entry, comment)
    if 'errorCode' in data:
        return error(request, data)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=deleted&entry=%s&comment=%s' % (entry, comment)
    else:
        next = next + '?message=deleted&entry=%s&comment=%s' % (entry, comment)
    next = next + '#%s' % entry
    return HttpResponseRedirect(next)

def comment_undelete(request, entry, comment):
    '''Un-delete a comment.
    
    Authentication is required.

    entry is the entry id.
    comment is the comment id.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.undelete_comment(entry, comment)
    if 'errorCode' in data:
        return error(request, data)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=commented&entry=%s&comment=%s' % (entry, comment)
    else:
        next = next + '?message=commented&entry=%s&comment=%s' % (entry, comment)
    next = next + '#%s' % comment
    return HttpResponseRedirect(next)

def entry(request, entry):
    '''View a single entry.
    
    entry is the entry id.
    '''
    if request.session.get('nickname', None):
        f = friendfeed.FriendFeed(request.session['nickname'],
            request.session['key'])
    else:
        f = friendfeed.FriendFeed()
    data = f.fetch_entry(entry)
    if 'errorCode' in data:
        return error(request, data)
    extra_context = {
        'entries': data['entries'],
        'permalink': True,
        'title': data['entries'][0]['title'],
    }
    return render_to_response('entry.html', extra_context, context_instance=RequestContext(request))

def entry_comment(request, entry):
    '''Comment on an entry.

    Authentication is required.

    entry is the entry id.
    An optional parameter, comment, in the GET dict will allow you to edit an
    entry.
    An optional parameter, body, in the GET dict will initialize the form.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            f = friendfeed.FriendFeed(request.session['nickname'],
                request.session['key'])
            if form.data['comment']:
                data = f.edit_comment(form.data['entry'], form.data['comment'], form.data['body'])
            else:
                data = f.add_comment(form.data['entry'], form.data['body'], via=VIA)
            if 'errorCode' in data:
                return error(request, data)
            next = form.data['next']
            comment = data['id']
            if not form.data['comment']:
                if '?' in next:
                    next = next + '&message=commented&entry=%s&comment=%s' % (entry, comment)
                else:
                    next = next + '?message=commented&entry=%s&comment=%s' % (entry, comment)
            next = next + '#%s' % comment
            return HttpResponseRedirect(next)
    else:
        initial = {
            'body': request.GET.get('body', None),
            'comment': request.GET.get('comment', None),
            'entry': entry,
            'next': request.GET.get('next', '/'),
        }
        form = CommentForm(initial=initial)
    extra_context = {
        'form': form,
    }
    return render_to_response('comment.html', extra_context, context_instance=RequestContext(request))

def entry_delete(request, entry):
    '''Delete an entry.

    Authentication is required.

    entry is the entry id.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.delete_entry(entry)
    if 'errorCode' in data:
        return error(request, data)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=deleted&entry=%s' % entry
    else:
        next = next + '?message=deleted&entry=%s' % entry
    next = next + '#%s' % entry
    return HttpResponseRedirect(next)

def entry_undelete(request, entry):
    '''Un-delete an entry.

    Authentication is required.

    entry is the entry id.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.undelete_entry(entry)
    if 'errorCode' in data:
        return error(request, data)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=shared&entry=%s' % entry
    else:
        next = next + '?message=shared&entry=%s' % entry
    next = next + '#%s' % entry
    return HttpResponseRedirect(next)

def entry_hide(request, entry):
    '''Hide an entry.

    Authentication is required.

    entry is the entry id to be hidden.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.hide_entry(entry)
    if 'errorCode' in data:
        return error(request, data)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=hidden&entry=%s' % entry
    else:
        next = next + '?message=hidden&entry=%s' % entry
    next = next + '#%s' % entry
    return HttpResponseRedirect(next)

def entry_like(request, entry):
    '''Like an entry.

    Authentication is required.

    entry is the entry id to be liked.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.add_like(entry)
    if 'errorCode' in data:
        return error(request, data)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=liked&entry=%s' % entry
    else:
        next = next + '?message=liked&entry=%s' % entry
    next = next + '#%s' % entry
    return HttpResponseRedirect(next)

def entry_unhide(request, entry):
    '''Un-hide an entry.

    Authentication is required.

    entry is the entry id to be un-hidden.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.unhide_entry(entry)
    if 'errorCode' in data:
        return error(request, data)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=un-hidden&entry=%s' % entry
    else:
        next = next + '?message=un-hidden&entry=%s' % entry
    next = next + '#%s' % entry
    return HttpResponseRedirect(next)

def entry_unlike(request, entry):
    '''Un-like an entry.

    Authentication is required.

    entry is the entry id to be un-liked.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.delete_like(entry)
    if 'errorCode' in data:
        return error(request, data)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=un-liked&entry=%s' % entry
    else:
        next = next + '?message=un-liked&entry=%s' % entry
    next = next + '#%s' % entry
    return HttpResponseRedirect(next)

def home(request):
    '''Render a users home feed.

    Authentication is required.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    start = max(get_integer_argument(request, 'start', 0), 0)
    num = get_integer_argument(request, 'num', NUM)
    data = f.fetch_home_feed(**querydict_to_dict(request.GET))
    if 'errorCode' in data:
        return error(request, data)
    entries = [entry for entry in data['entries'] if not entry['hidden']]
    hidden = [entry for entry in data['entries'] if entry['hidden']]
    new_start = start
    while len(entries) < num and (new_start - start) / num < 3:
        new_start = new_start + num
        kwargs = querydict_to_dict(request.GET)
        kwargs['start'] = new_start
        data = f.fetch_home_feed(**kwargs)
        if 'errorCode' in data:
            break
        more_entries = [entry for entry in data['entries'] if not entry['hidden']]
        more_hidden = [entry for entry in data['entries'] if entry['hidden']]
        entries.extend(more_entries)
        hidden.extend(more_hidden)
    entries = entries[:num]
    extra_context = {
        'entries': entries,
        'next': start + len(entries) + len(hidden),
        'hidden': hidden,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = max(start - num, 0)
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('home.html', extra_context, context_instance=RequestContext(request))

def login(request):
    '''Log a user in.
    '''
    extra_context = {}
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            nickname = form.data['nickname'].strip().lower()
            f = friendfeed.FriendFeed(nickname, form.data['key'])
            data = f.validate()
            if 'errorCode' in data:
                return error(request, data)
            request.session['nickname'] = nickname
            request.session['key'] = form.data['key']
            return HttpResponseRedirect('/?message=settings')
    else:
        form = LoginForm()
    extra_context['form'] = form
    return render_to_response('login.html', extra_context, context_instance = RequestContext(request))

def logout(request):
    '''Log a user out.
    '''
    request.session['nickname'] = None
    request.session['key'] = None
    return HttpResponseRedirect('/')

def public(request):
    ''' Render the public feed.

    Authentication is not required and not used.  Memcache saves this data so
    we don't have to hit FriendFeed as often for it.
    '''
    f = friendfeed.FriendFeed()
    start = max(get_integer_argument(request, 'start', 0), 0)
    num = get_integer_argument(request, 'num', NUM)
    key = 'public_%i_%i_%s' % (num, start, service)
    try:
        data = memcache.get(key)
    except:
        data = None
    if not data:
        data = f.fetch_public_feed(**querydict_to_dict(request.GET))
        if 'errorCode' in data:
            return error(request, data)
        memcache.set(key, data, PUBLIC_CACHE_TIME)
    entries = data['entries']
    extra_context = {
        'entries': entries,
        'next': start + num,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = max(start - num, 0)
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('public.html', extra_context, context_instance=RequestContext(request))

def related(request):
    url = request.GET.get('url', None)
    if not url:
        raise Http404
    if request.session.get('nickname', None):
        f = friendfeed.FriendFeed(request.session['nickname'],
            request.session['key'])
    else:
        f = friendfeed.FriendFeed()
    start = max(get_integer_argument(request, 'start', 0), 0)
    num = get_integer_argument(request, 'num', NUM)
    data = f.fetch_url_feed(url, **querydict_to_dict(request.GET))
    if 'errorCode' in data:
        return error(request, data)
    extra_context = {
        'entries': data['entries'],
        'next': start + num,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = max(start - num, 0)
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('related.html', extra_context, context_instance=RequestContext(request))

def room(request, nickname):
    '''Render a room feed.

    Authentication is not required but is used if set.

    nickname is the room's nickname.
    '''
    if request.session.get('nickname', None):
        f = friendfeed.FriendFeed(request.session['nickname'],
            request.session['key'])
    else:
        f = friendfeed.FriendFeed()
    start = max(get_integer_argument(request, 'start', 0), 0)
    num = get_integer_argument(request, 'num', NUM)
    data = f.fetch_room_feed(nickname, **querydict_to_dict(request.GET))
    if 'errorCode' in data:
        return error(request, data)
    profile = f.fetch_room_profile(nickname)
    entries = [entry for entry in data['entries'] if not entry['hidden']]
    hidden = [entry for entry in data['entries'] if entry['hidden']]
    extra_context = {
        'entries': entries,
        'next': start + num,
        'hidden': hidden,
        'profile': profile,
        'room': nickname,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = max(start - num, 0)
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('room.html', extra_context, context_instance=RequestContext(request))

def list(request, nickname):
    '''Render a list feed.

    Authentication is required.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    start = max(get_integer_argument(request, 'start', 0), 0)
    num = get_integer_argument(request, 'num', NUM)
    data = f.fetch_list_feed(nickname, **querydict_to_dict(request.GET))
    if 'errorCode' in data:
        return error(request, data)
    profile = f.fetch_list_profile(nickname)
    entries = [entry for entry in data['entries'] if not entry['hidden']]
    hidden = [entry for entry in data['entries'] if entry['hidden']]
    extra_context = {
        'entries': entries,
        'next': start + num,
        'hidden': hidden,
        'profile': profile,
        'list': nickname,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = max(start - num, 0)
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('list.html', extra_context, context_instance=RequestContext(request))

def lists(request):
    '''Display the authenticated users lists
    
    Authentication is required.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.fetch_user_profile(request.session['nickname'])
    if 'errorCode' in data:
        return error(request, data)
    extra_context = {
        'lists': data['lists'],
    }
    return render_to_response('lists.html', extra_context, context_instance=RequestContext(request))

def rooms(request):
    '''Display the authenticated users rooms page or a list of the users rooms

    Authentication is required.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    if 'list' in request.GET:
        data = f.fetch_user_profile(request.session['nickname'])
        if not 'errorCode' in data:
            extra_context = {
                'rooms': data['rooms'],
            }
            template = 'rooms_list.html'
    else:
        start = max(get_integer_argument(request, 'start', 0), 0)
        num = get_integer_argument(request, 'num', NUM)
        data = f.fetch_rooms_feed(num=num, **querydict_to_dict(request.GET))
        if not 'errorCode' in data:
            entries = [entry for entry in data['entries'] if not entry['hidden']]
            hidden = [entry for entry in data['entries'] if entry['hidden']]
            extra_context = {
                'entries': entries,
                'hidden': hidden,
                'next': start + num,
            }
            if start > 0:   
                extra_context['has_previous'] = True
                extra_context['previous'] = max(start - num, 0)
            template = 'rooms.html'
    if 'errorCode' in data:
        return error(request, data)
    return render_to_response(template, extra_context, context_instance=RequestContext(request))

def search(request):
    '''Render a search feed.

    Authentication is not required but is used if set.

    Search operates on a 'search' paramater in the GET dict that works the same
    way the FriendFeed search works (who:everyone would search the public feed).
    ''' 
    if not 'q' in request.GET:
        initial = {}
        if request.session.get('nickname', None):
            initial['q'] = 'friends:%s' % request.session['nickname']
        extra_context = {
            'form': SearchForm(initial=initial),
        }
        return render_to_response('search_form.html', extra_context, context_instance=RequestContext(request))
    else:
        form = SearchForm(request.GET)
        if not form.is_valid():
            extra_context = {
                'form': form,
            }
            return render_to_response('search_form.html', extra_context, context_instance=RequestContext(request))
    if request.session.get('nickname', None):
        f = friendfeed.FriendFeed(request.session['nickname'],
            request.session['key'])
    else:
        f = friendfeed.FriendFeed()
    start = max(get_integer_argument(request, 'start', 0), 0)
    num = get_integer_argument(request, 'num', NUM)
    q = form.data['q']
    data = f.search(q, **querydict_to_dict(request.GET))
    if 'errorCode' in data:
        return error(request, data)
    entries = [entry for entry in data['entries'] if not entry['hidden']]
    hidden = [entry for entry in data['entries'] if entry['hidden']]
    extra_context = {
        'entries': entries,
        'hidden': hidden,
        'next': start + num,
        'title': q,
        'form': form,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = max(start - num, 0)
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('search.html', extra_context, context_instance=RequestContext(request))

def settings(request):
    '''Set a number of settings.
    
    Authentication is not required (because these settings are just stored in
    a session; not on a user object).
    '''
    extra_context = {}
    if request.method == 'POST':
        form = SettingsForm(request.POST)
        if form.is_valid():
            request.session['fontsize'] = form.data['fontsize']
            request.session['googlemobileproxy'] = form.data.get('googlemobileproxy', GMP)
            request.session['newwindow'] = form.data.get('newwindow', NEW_WINDOW)
            request.session['num'] = form.data['num']
            request.session['nomedia'] = form.data.get('nomedia', NO_MEDIA)
            extra_context['saved'] = True
    else:
        initial = {
            'fontsize': int(request.session.get('fontsize', FONT_SIZE)),
            'googlemobileproxy': request.session.get('googlemobileproxy', GMP),
            'newwindow': request.session.get('newwindow', NEW_WINDOW),
            'num': int(request.session.get('num', 30)),
            'nomedia': request.session.get('nomedia', NO_MEDIA),
        }
        form = SettingsForm(initial=initial)
    extra_context['form'] = form
    return render_to_response('settings.html', extra_context, context_instance = RequestContext(request))

def share(request):
    '''Publish a message to the users feed or a room (if 'room' is set in the
    POST dict.

    Authentication is required.
    '''
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    if request.method == 'POST':
        if 'title' in request.POST:
            data = f.publish_message(request.POST['title'], via=VIA, room=request.POST.get('room', None))
            if 'errorCode' in data:
                return error(request, data)
    next = request.POST.get('next', '/')
    if '?' in next:
        next = next + '&message=shared&entry=%s' % data['entries'][0]['id']
    else:
        next = next + '?message=shared&entry=%s' % data['entries'][0]['id']
    next += '#%s' % data['entries'][0]['id']
    return HttpResponseRedirect(next)

def user(request, nickname, type=None):
    '''Render a users feed.

    Authentication is not required but is used if set.

    nickname is the user's nickname.
    type can be None (default), 'comments', 'likes', 'discussion', or 'friends'
    '''
    if request.session.get('nickname', None):
        f = friendfeed.FriendFeed(request.session['nickname'],
            request.session['key'])
        key = 'profile/' + request.session['nickname']
        try:
            current_user = memcache.get(key)
        except:
            current_user = None
        if not current_user:
            current_user = f.fetch_user_profile(request.session['nickname']) 
            memcache.set(key, current_user, 60*60)
        subscriptions = [s['nickname'] for s in current_user['subscriptions']]
        subscribed = nickname in subscriptions
    else:
        f = friendfeed.FriendFeed()
        subscribed = False
    start = max(get_integer_argument(request, 'start', 0), 0)
    num = get_integer_argument(request, 'num', NUM)
    kwargs = querydict_to_dict(request.GET)
    if type == 'comments':
        data = f.fetch_user_comments_feed(nickname, **kwargs)
    elif type == 'likes':
        data = f.fetch_user_likes_feed(nickname, **kwargs)
    elif type == 'discussion':
        data = f.fetch_user_discussion_feed(nickname, **kwargs)
    elif type == 'friends':
        data = f.fetch_user_friends_feed(nickname, **kwargs)
    else:
        data = f.fetch_user_feed(nickname, **kwargs)
    try:
        profile = f.fetch_user_profile(nickname)
    except:
        profile = {
            'name': data['entries'][0]['user']['name'],
        }
    if 'errorCode' in data:
        return error(request, data)
    entries = [entry for entry in data['entries'] if not entry['hidden']]
    hidden = [entry for entry in data['entries'] if entry['hidden']]
    extra_context = {
        'entries': entries,
        'hidden': hidden,
        'next': start + num,
        'profile': profile,
        'subscribed': subscribed,
        'type': type,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = max(start - num, 0)
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('user.html', extra_context, context_instance=RequestContext(request))

def user_subscribe(request, nickname):
    '''Subscribe to a user.

    Authentication is required.
    '''
    if not request.method == 'POST':
        return HttpResponseRedirect(reverse('user', args=[nickname]))
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.user_subscribe(nickname)
    if 'errorCode' in data:
        return error(request, data)
    memcache.delete('profile/' + request.session['nickname'])
    args = {
        'message': data.get('status', '')
    }
    return HttpResponseRedirect(reverse('user', args=[nickname]) + '?' + urllib.urlencode(args))

def user_unsubscribe(request, nickname):
    '''Unsubscribe to a user.

    Authentication is required.
    '''
    if not request.method == 'POST':
        return HttpResponseRedirect(reverse('user', args=[nickname]))
    if not request.session.get('nickname', None):
        return HttpResponseRedirect(reverse('login'))
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    data = f.user_unsubscribe(nickname)
    if 'errorCode' in data:
        return error(request, data)
    memcache.delete('profile/' + request.session['nickname'])
    args = {
        'message': data.get('status', '')
    }
    return HttpResponseRedirect(reverse('user', args=[nickname]) + '?' + urllib.urlencode(args))
