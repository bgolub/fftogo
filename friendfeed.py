#!/usr/bin/env python
#
# Copyright 2008 FriendFeed
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Methods to interact with the FriendFeed API

Detailed documentation is available at http://friendfeed.com/api/.

Many parts of the FriendFeed API require authentication. To support
authentication, FriendFeed gives users a "remote key" that they give to
third party applications to access FriendFeed. The user's nickname and that
remote key are passed as arguments to the constructor of the FriendFeed class,
and the credentials are automatically passed to all called methods. For
example:

    session = friendfeed.FriendFeed(nickname, remote_key)
    entry = session.publish_message("Testing the FriendFeed API")

Users can get their remote key from http://friendfeed.com/remotekey. You
should direct users who don't know their remote key to that page.
For guidelines on user interface and terminology, check out
http://friendfeed.com/api/guidelines.
"""

import base64
import datetime
import time
import urllib
# Google App Engine does not allow urllib2; we use urlfetch instead
from google.appengine.api import urlfetch

# We require a JSON parsing library. These seem to be the most popular.
try:
    import cjson
    parse_json = lambda s: cjson.decode(s.decode("utf-8"), True)
except ImportError:
    try:
        # Django includes simplejson
        from django.utils import simplejson
        parse_json = lambda s: simplejson.loads(s.decode("utf-8"))
    except ImportError:
        import json
        parse_json = lambda s: _unicodify(json.read(s))


class FriendFeed(object):
    def __init__(self, auth_nickname=None, auth_key=None):
        """Creates a new FriendFeed session for the given user.

        The credentials are optional for some operations, but required for
        private feeds and all operations that write data, like publish_link.
        """
        self.auth_nickname = auth_nickname
        self.auth_key = auth_key

    def validate(self):
        """Validate the credentials."""
        return self._fetch("/api/validate", None)

    def hide_entry(self, entry_id):
        """Hides the entry with the given ID."""
        return self._fetch("/api/entry/hide", {
            "entry": entry_id,
        })
 
    def unhide_entry(self, entry_id):
        """Un-hides the entry with the given ID."""
        return self._fetch("/api/entry/hide", {
            "entry": entry_id,
            "unhide": '1',
        })
 
    def delete_entry(self, entry_id):
        """Deletes the entry with the given ID."""
        return self._fetch("/api/entry/delete", {
            "entry": entry_id,
        })
 
    def undelete_entry(self, entry_id):
        """Un-deletes the entry with the given ID."""
        return self._fetch("/api/entry/delete", {
            "entry": entry_id,
            "undelete": '1',
        })

    def fetch_entry(self, entry_id):
        return self._fetch_feed(
            "/api/feed/entry/" + urllib.quote_plus(entry_id))

    def fetch_user_profile(self, nickname):
        """Returns a users profile for the given nickname.

        Authentication is required for private users.
        """
        return self._fetch(
            "/api/user/" + urllib.quote_plus(nickname) + "/profile", None)

    def fetch_room_profile(self, nickname):
        """Returns a rooms profile for the given nickname.

        Authentication *should* be required for private rooms but will always
        401 at the moment.
        """
        return self._fetch(
            "/api/room/" + urllib.quote_plus(nickname) + "/profile", None)

    def fetch_room_feed(self, nickname, **kwargs):
        """Returns a rooms feed with the given room nickname

        Authentication is required for private rooms.
        """
        return self._fetch_feed(
            "/api/feed/room/" + urllib.quote_plus(nickname), **kwargs)

    def fetch_public_feed(self, **kwargs):
        """Returns the public feed with everyone's public entries.

        Authentication is not required.
        """
        return self._fetch_feed("/api/feed/public", **kwargs)

    def fetch_user_feed(self, nickname, **kwargs):
        """Returns the entries shared by the user with the given nickname.

        Authentication is required if the user's feed is not public.
        """
        return self._fetch_feed(
            "/api/feed/user/" + urllib.quote_plus(nickname), **kwargs)

    def fetch_user_comments_feed(self, nickname, **kwargs):
        """Returns the entries the given user has commented on."""
        return self._fetch_feed(
            "/api/feed/user/" + urllib.quote_plus(nickname) + "/comments",
            **kwargs)

    def fetch_user_likes_feed(self, nickname, **kwargs):
        """Returns the entries the given user has "liked"."""
        return self._fetch_feed(
            "/api/feed/user/" + urllib.quote_plus(nickname) + "/likes",
            **kwargs)

    def fetch_user_discussion_feed(self, nickname, **kwargs):
        """Returns the entries the given user has commented on or "liked"."""
        return self._fetch_feed(
            "/api/feed/user/" + urllib.quote_plus(nickname) + "/discussion",
            **kwargs)

    def fetch_multi_user_feed(self, nicknames, **kwargs):
        """Returns a merged feed with all of the given users' entries.

        Authentication is required if any one of the users' feeds is not
        public.
        """
        return self._fetch_feed("/api/feed/user", nickname=",".join(nicknames),
                                **kwargs)

    def fetch_home_feed(self, **kwargs):
        """Returns the entries the authenticated user sees on their home page.

        Authentication is always required.
        """
        return self._fetch_feed("/api/feed/home", **kwargs)

    def search(self, q, **kwargs):
        """Searches over entries in FriendFeed.

        If the request is authenticated, the default scope is over all of the
        entries in the authenticated user's Friends Feed. If the request is
        not authenticated, the default scope is over all public entries.

        The query syntax is the same syntax as
        http://friendfeed.com/advancedsearch
        """
        kwargs["q"] = q
        return self._fetch_feed("/api/feed/search", **kwargs)

    def publish_message(self, message, **kwargs):
        """Publishes the given message to the authenticated user's feed.

        See publish_link for additional options.
        """
        return self.publish_link(title=message, link=None, **kwargs)

    def publish_link(self, title, link, comment=None, image_urls=[],
                     images=[], via=None, audio_urls=[], audio=[],
                     room=None):
        """Publishes the given link/title to the authenticated user's feed or
        to a room.

        Authentication is always required.

        image_urls is a list of URLs that will be downloaded and included as
        thumbnails beneath the link. The thumbnails will all link to the
        destination link. If you would prefer that the images link somewhere
        else, you can specify images[] instead, which should be a list of
        dicts of the form {"url": ..., "link": ...}. The thumbnail with the
        given url will link to the specified link.

        audio_urls is a list of MP3 URLs that will show up as a play
        button beneath the link. You can optionally supply audio[]
        instead, which should be a list of dicts of the form
        {"url": ..., "title": ...}. The given title will appear when the
        audio file is played.

        We return the parsed/published entry as returned from the server, which
        includes the final thumbnail URLs as well as the ID for the new entry.

        Example:

            session = friendfeed.FriendFeed(nickname, remote_key)
            entry = session.publish_link(
                title="Testing the FriendFeed API",
                link="http://friendfeed.com/",
                image_urls=[
                    "http://friendfeed.com/static/images/jim-superman.jpg",
                    "http://friendfeed.com/static/images/logo.png",
                ],
            )
            print "Posted images at http://friendfeed.com/e/%s" % entry["id"]
        """
        post_args = {"title": title}
        if link:
            post_args["link"] = link
        if comment:
            post_args["comment"] = comment
        if via:
            post_args["via"] = via
        images = images[:]
        for image_url in image_urls:
            images.append({"url": image_url})
        for i, image in enumerate(images):
            post_args["image%d_url" % i] = image["url"]
            if image.get("link"):
                post_args["image%d_link" % i] = image["link"]
        audio = audio[:]
        for audio_url in audio_urls:
            audio.append({"url": audio_url})
        for i, clip in enumerate(audio):
            post_args["audio%d_url" % i] = clip["url"]
            if clip.get("title"):
                post_args["audio%d_title" % i] = clip["title"]
        if room:
            post_args["room"] = room
        return self._fetch_feed("/api/share", post_args=post_args)

    def add_comment(self, entry_id, body, via=None):
        """Adds the given comment to the entry with the given ID.

        We return the ID of the new comment, which can be used to edit or
        delete the comment.
        """
        args = {
            "entry": entry_id,
            "body": body
        }
        if via: args["via"] = via
        return self._fetch("/api/comment", args)

    def edit_comment(self, entry_id, comment_id, body):
        """Updates the comment with the given ID."""
        return self._fetch("/api/comment", {
            "entry": entry_id,
            "comment": comment_id,
            "body": body
        })

    def delete_comment(self, entry_id, comment_id):
        """Deletes the comment with the given ID."""
        return self._fetch("/api/comment/delete", {
            "entry": entry_id,
            "comment": comment_id,
        })

    def undelete_comment(self, entry_id, comment_id):
        """Un-deletes the comment with the given ID."""
        return self._fetch("/api/comment/delete", {
            "entry": entry_id,
            "comment": comment_id,
            "undelete": 1,
        })

    def add_like(self, entry_id):
        """'Likes' the entry with the given ID."""
        return self._fetch("/api/like", {
            "entry": entry_id,
        })

    def delete_like(self, entry_id):
        """Deletes the 'Like' for the entry with the given ID (if any)."""
        return self._fetch("/api/like/delete", {
            "entry": entry_id,
        })

    def _fetch_feed(self, uri, post_args=None, **kwargs):
        """Publishes to the given URI and parses the returned JSON feed."""
        # Parse all the dates in the result JSON
        result = self._fetch(uri, post_args, **kwargs)
        rfc3339_date = "%Y-%m-%dT%H:%M:%SZ"
        date_properties = frozenset(("updated", "published"))
        for entry in result.get("entries", []):
            entry["updated"] = self._parse_date(entry["updated"])
            entry["published"] = self._parse_date(entry["published"])
            for comment in entry.get("comments", []):
                comment["date"] = self._parse_date(comment["date"])
            for like in entry.get("likes", []):
                like["date"] = self._parse_date(like["date"])
        return result

    def _fetch(self, uri, post_args, **url_args):
        # Use Django's urlencode because it is unicode safe
        from django.utils.http import urlencode
        url_args["format"] = "json"
        args = urlencode(url_args)
        url = "http://friendfeed.com" + uri + "?" + args
        headers = {}
        if post_args is not None:
            # If we are POSTing then set the method/content-type (urllib2
            # does this for you but urlfetch does not)
            payload = urlencode(post_args)
            method = urlfetch.POST
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            payload = None
            method = urlfetch.GET
        if self.auth_nickname and self.auth_key:
            pair = "%s:%s" % (self.auth_nickname, self.auth_key)
            token = base64.b64encode(pair)
            headers["Authorization"] = "Basic %s" % token
        result = urlfetch.fetch(url, payload=payload, method=method,
            headers=headers)
        data = parse_json(result.content)
        data['statusCode'] = result.status_code
        return data

    def _parse_date(self, date_str):
        rfc3339_date = "%Y-%m-%dT%H:%M:%SZ"
        return datetime.datetime(*time.strptime(date_str, rfc3339_date)[:6])


def _unicodify(json):
    """Makes all strings in the given JSON-like structure unicode."""
    if isinstance(json, str):
        return json.decode("utf-8")
    elif isinstance(json, dict):
        for name in json:
            json[name] = _unicodify(json[name])
    elif isinstance(json, list):
        for part in json:
            _unicodify(part)
    return json


def _example():
    # Fill in a nickname and a valid remote key below for authenticated
    # actions like posting an entry and reading a protected feed
    # session = FriendFeed(auth_nickname=nickname, auth_key=remote_key)
    session = FriendFeed()

    feed = session.fetch_public_feed()
    # feed = session.fetch_user_feed("bret")
    # feed = session.fetch_user_feed("paul", service="twitter")
    # feed = session.fetch_user_discussion_feed("bret")
    # feed = session.fetch_multi_user_feed(["bret", "paul", "jim"])
    # feed = session.search("who:bret friendfeed")
    for entry in feed["entries"]:
        print entry["published"].strftime("%m/%d/%Y"), entry["title"]

    if session.auth_nickname and session.auth_key:
        # The feed that the authenticated user would see on their home page
        feed = session.fetch_home_feed()

        # Post a message on this user's feed
        entry = session.publish_message("Testing the FriendFeed API")
        print "Posted new message at http://friendfeed.com/e/%s" % entry["id"]

        # Post a link on this user's feed
        entry = session.publish_link(title="Testing the FriendFeed API",
                                     link="http://friendfeed.com/")
        print "Posted new link at http://friendfeed.com/e/%s" % entry["id"]

        # Post a link with two thumbnails on this user's feed
        entry = session.publish_link(
            title="Testing the FriendFeed API",
            link="http://friendfeed.com/",
            image_urls=[
                "http://friendfeed.com/static/images/jim-superman.jpg",
                "http://friendfeed.com/static/images/logo.png",
            ],
        )
        print "Posted images at http://friendfeed.com/e/%s" % entry["id"]


if __name__ == "__main__":
    _example()
