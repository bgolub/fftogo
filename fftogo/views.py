from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import feedgenerator
from google.appengine.api import memcache

import friendfeed

CACHE_TIME = 30
NUM = 30
VIA = 'fftogo'

def atom(entries):
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
            description = '<a href="http://friendfeed.com/e/%s">View in FriendFeed</a>' % entry['id'],
            author_name = entry['user']['name'],
            pubdate = entry['updated'],
        )
    return HttpResponse(f.writeString('utf-8'))

def comment_delete(request, entry, comment):
    if not request.session.get('nickname', None):
        return HttpResponseRedirect('/login/')
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    try:
        f.delete_comment(entry, comment)
    except Exception, e:
        if e[0] == 401:
            del request.session['nickname']
            del request.session['key']
        return HttpResponseRedirect('/%s/' % e)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=deleted&entry=%s&comment=%s' % (entry, comment)
    else:
        next = next + '?message=deleted&entry=%s&comment=%s' % (entry, comment)
    next = next + '#%s' % entry
    return HttpResponseRedirect(next)

def comment_restore(request, entry, comment):
    if not request.session.get('nickname', None):
        return HttpResponseRedirect('/login/')
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    try:
        f.undelete_comment(entry, comment)
    except Exception, e:
        if e[0] == 401:
            del request.session['nickname']
            del request.session['key']
        return HttpResponseRedirect('/%s/' % e)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=commented&entry=%s&comment=%s' % (entry, comment)
    else:
        next = next + '?message=commented&entry=%s&comment=%s' % (entry, comment)
    next = next + '#%s' % comment
    return HttpResponseRedirect(next)

def entry_comment(request, entry):
    if not request.session.get('nickname', None):
        return HttpResponseRedirect('/login/')
    from fftogo.forms import CommentForm
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            f = friendfeed.FriendFeed(request.session['nickname'],
                request.session['key'])
            try:
                comment = f.add_comment(form.data['entry'], form.data['body'], via=VIA)
            except Exception, e:
                if e[0] == 401:
                    del request.session['nickname']
                    del request.session['key']
                return HttpResponseRedirect('/%s/' % e)
            next = form.data['next']
            if '?' in next:
                next = next + '&message=commented&entry=%s&comment=%s' % (entry, comment)
            else:
                next = next + '?message=commented&entry=%s&comment=%s' % (entry, comment)
            next = next + '#%s' % comment
            return HttpResponseRedirect(next)
    else:
        initial = {
            'entry': entry,
            'next': request.GET.get('next', '/'),
        }
        form = CommentForm(initial=initial)
    extra_context = {
        'form': form,
    }
    return render_to_response('comment.html', extra_context, context_instance=RequestContext(request))

def entry_like(request, entry):
    if not request.session.get('nickname', None):
        return HttpResponseRedirect('/login/')
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    try:
        f.add_like(entry)
    except Exception, e:
        if e[0] == 401:
            del request.session['nickname']
            del request.session['key']
        return HttpResponseRedirect('/%s/' % e)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=liked&entry=%s' % entry
    else:
        next = next + '?message=liked&entry=%s' % entry
    next = next + '#%s' % entry
    return HttpResponseRedirect(next)

def entry_unlike(request, entry):
    if not request.session.get('nickname', None):
        return HttpResponseRedirect('/login/')
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    try:
        f.delete_like(entry)
    except Exception, e:
        if e[0] == 401:
            del request.session['nickname']
            del request.session['key']
        return HttpResponseRedirect('/%s/' % e)
    next = request.GET.get('next', '/')
    if '?' in next:
        next = next + '&message=un-liked&entry=%s' % entry
    else:
        next = next + '?message=un-liked&entry=%s' % entry
    next = next + '#%s' % entry
    return HttpResponseRedirect(next)

def home(request):
    if not request.session.get('nickname', None):
        return HttpResponseRedirect('/login/')
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    try:
        start = int(request.GET.get('start', 0))
    except:
        start = 0
    service = request.GET.get('service', None)
    num = int(request.session.get('num', NUM))
    try:
        data = f.fetch_home_feed(num=num, start=start, service=service)
    except Exception, e:
        if e[0] == 401:
            del request.session['nickname']
            del request.session['key']
        return HttpResponseRedirect('/%s/' % e)
    entries = [entry for entry in data['entries'] if not entry['hidden']]
    hidden = [entry for entry in data['entries'] if entry['hidden']]
    extra_context = {
        'entries': entries,
        'next': start + num,
        'hidden': hidden,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = start - num
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('home.html', extra_context, context_instance=RequestContext(request))

def login(request):
    from fftogo.forms import LoginForm
    extra_context = {}
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            try:
                nickname = form.data['nickname'].strip()
                f = friendfeed.FriendFeed(nickname, form.data['key'])
                data = f.fetch_home_feed(num=1)
                request.session['nickname'] = nickname
                request.session['key'] = form.data['key']
                return HttpResponseRedirect('/?message=settings')
            except Exception, e:
                if e[0] == 401:
                    del request.session['nickname']
                    del request.session['key']
                return HttpResponseRedirect('/%s/' % e)
    else:
        form = LoginForm()
    extra_context['form'] = form
    return render_to_response('login.html', extra_context, context_instance = RequestContext(request))

def logout(request):
    request.session['nickname'] = None
    request.session['key'] = None
    return HttpResponseRedirect('/')

def public(request):
    f = friendfeed.FriendFeed()
    try:
        start = int(request.GET.get('start', 0))
    except:
        start = 0
    service = request.GET.get('service', None)
    num = int(request.session.get('num', NUM))
    key = 'public_%i_%i_%s' % (num, start, service)
    try:
        data = memcache.get(key)
    except:
        data = None
    if not data:
        try:
            data = f.fetch_public_feed(num=num, start=start, service=service)
        except Exception, e:
            if e[0] == 401:
                del request.session['nickname']
                del request.session['key']
            return HttpResponseRedirect('/%s/' % e)
        memcache.set(key, data, CACHE_TIME)
    entries = data['entries']
    extra_context = {
        'entries': entries,
        'next': start + num,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = start - num
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('public.html', extra_context, context_instance=RequestContext(request))

def room(request, nickname):
    if request.session.get('nickname', None):
        f = friendfeed.FriendFeed(request.session['nickname'],
            request.session['key'])
    else:
        f = friendfeed.FriendFeed()
    try:
        start = int(request.GET.get('start', 0))
    except:
        start = 0
    service = request.GET.get('service', None)
    num = int(request.session.get('num', NUM))
    try:
        data = f.fetch_room_feed(nickname, num=num, start=start,
            service=service)
        profile = f.fetch_room_profile(nickname)
    except Exception, e:
        if e[0] == 401:
            del request.session['nickname']
            del request.session['key']
        return HttpResponseRedirect('/%s/' % e)
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
        extra_context['previous'] = start - num
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('room.html', extra_context, context_instance=RequestContext(request))

def rooms(request):
    if not request.session.get('nickname', None):
        return HttpResponseRedirect('/login/')
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    try:
        data = f.fetch_user_profile(request.session['nickname'])
    except Exception, e:
        if e[0] == 401:
            del request.session['nickname']
            del request.session['key']
        return HttpResponseRedirect('/%s/' % e)
    extra_context = {
        'rooms': data['rooms'],
    }
    return render_to_response('rooms.html', extra_context, context_instance=RequestContext(request))

def search(request):
    from fftogo.forms import SearchForm
    if not 'search' in request.GET:
        extra_context = {
            'form': SearchForm(),
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
    try:
        start = int(request.GET.get('start', 0))
    except:
        start = 0
    service = request.GET.get('service', None)
    num = int(request.session.get('num', NUM))
    search = form.data['search']
    try:
        data = f.search(search, num=num, start=start, service=service)
    except Exception, e:
        if e[0] == 401:
            del request.session['nickname']
            del request.session['key']
        return HttpResponseRedirect('/%s/' % e)
    entries = [entry for entry in data['entries'] if not entry['hidden']]
    hidden = [entry for entry in data['entries'] if entry['hidden']]
    extra_context = {
        'entries': entries,
        'hidden': hidden,
        'next': start + num,
        'title': search,
        'form': form,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = start - num
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('search.html', extra_context, context_instance=RequestContext(request))

def settings(request):
    from fftogo.forms import SettingsForm
    extra_context = {}
    if request.method == 'POST':
        form = SettingsForm(request.POST)
        if form.is_valid():
            request.session['fontsize'] = form.data['fontsize']
            request.session['googlemobileproxy'] = form.data.get('googlemobileproxy', False)
            request.session['newwindow'] = form.data.get('newwindow', False)
            request.session['num'] = form.data['num']
    else:
        initial = {
            'fontsize': int(request.session.get('fontsize', 10)),
            'newwindow': request.session.get('newwindow', False),
            'googlemobileproxy': request.session.get('googlemobileproxy', False),
            'num': int(request.session.get('num', 30)),
        }
        form = SettingsForm(initial=initial)
    extra_context['form'] = form
    return render_to_response('settings.html', extra_context, context_instance = RequestContext(request))

def share(request):
    if not request.session.get('nickname', None):
        return HttpResponseRedirect('/login/')
    f = friendfeed.FriendFeed(request.session['nickname'],
        request.session['key'])
    if request.method == 'POST':
        if 'title' in request.POST:
            try:
                entry = f.publish_message(request.POST['title'], via=VIA, room=request.POST.get('room', None))
            except Exception, e:
                if e[0] == 401:
                    del request.session['nickname']
                    del request.session['key']
                return HttpResponseRedirect('/%s/' % e)
    next = request.POST.get('next', '/')
    if '?' in next:
        next = next + '&message=created'
    else:
        next = next + '?message=created'
    next += '#%s' % entry['id'] 
    return HttpResponseRedirect(next)

def user(request, nickname, type=None):
    if request.session.get('nickname', None):
        f = friendfeed.FriendFeed(request.session['nickname'],
            request.session['key'])
    else:
        f = friendfeed.FriendFeed()
    try:
        start = int(request.GET.get('start', 0))
    except:
        start = 0
    service = request.GET.get('service', None)
    num = int(request.session.get('num', NUM))
    try:
        if type == 'comments':
            data = f.fetch_user_comments_feed(nickname, num=num, start=start,
                service=service)
        elif type == 'likes':
            data = f.fetch_user_likes_feed(nickname, num=num, start=start,
                service=service)
        elif type == 'discussion':
            data = f.fetch_user_discussion_feed(nickname, num=num, start=start,
                service=service)
        else:
            data = f.fetch_user_feed(nickname, num=num, start=start,
                service=service)
        profile = f.fetch_user_profile(nickname)
    except Exception, e:
        if e[0] == 401:
            del request.session['nickname']
            del request.session['key']
        return HttpResponseRedirect('/%s/' % e)
    entries = [entry for entry in data['entries'] if not entry['hidden']]
    hidden = [entry for entry in data['entries'] if entry['hidden']]
    extra_context = {
        'entries': entries,
        'hidden': hidden,
        'next': start + num,
        'profile': profile,
        'type': type,
    }
    if start > 0:
        extra_context['has_previous'] = True
        extra_context['previous'] = start - num
    if request.GET.get('output', 'html') == 'atom':
        return atom(entries)
    return render_to_response('user.html', extra_context, context_instance=RequestContext(request))
