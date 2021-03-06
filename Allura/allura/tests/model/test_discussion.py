# -*- coding: utf-8 -*-
"""
Model tests for artifact
"""
from cStringIO import StringIO
import time
from datetime import datetime
from cgi import FieldStorage

from pylons import c, g, request, response
from nose.tools import assert_raises, assert_equals, with_setup
import mock

from ming.orm.ormsession import ThreadLocalORMSession
from webob import Request, Response, exc

from allura import model as M
from allura.lib.app_globals import Globals
from allura.lib import helpers as h
from allura.tests import TestController
from alluratest.controller import setup_global_objects

def setUp():
    controller = TestController()
    controller.setUp()
    controller.app.get('/wiki/Home/')
    setup_global_objects()
    ThreadLocalORMSession.close_all()
    h.set_context('test', 'wiki', neighborhood='Projects')
    ThreadLocalORMSession.flush_all()
    ThreadLocalORMSession.close_all()


def tearDown():
    ThreadLocalORMSession.close_all()

@with_setup(setUp, tearDown)
def test_discussion_methods():
    d = M.Discussion(shortname='test', name='test')
    assert d.thread_class() == M.Thread
    assert d.post_class() == M.Post
    assert d.attachment_class() == M.DiscussionAttachment
    ThreadLocalORMSession.flush_all()
    d.update_stats()
    ThreadLocalORMSession.flush_all()
    assert d.last_post == None
    assert d.url().endswith('wiki/_discuss/')
    assert d.index()['name_s'] == 'test'
    assert d.subscription() == None
    assert d.find_posts().count() == 0
    jsn = d.__json__()
    assert jsn['name'] == d.name
    d.delete()
    ThreadLocalORMSession.flush_all()
    ThreadLocalORMSession.close_all()

@with_setup(setUp, tearDown)
def test_thread_methods():
    d = M.Discussion(shortname='test', name='test')
    t = M.Thread(discussion_id=d._id, subject='Test Thread')
    assert t.discussion_class() == M.Discussion
    assert t.post_class() == M.Post
    assert t.attachment_class() == M.DiscussionAttachment
    p0 = t.post('This is a post')
    p1 = t.post('This is another post')
    time.sleep(0.25)
    p2 = t.post('This is a reply', parent_id=p0._id)
    ThreadLocalORMSession.flush_all()
    ThreadLocalORMSession.close_all()
    d = M.Discussion.query.get(shortname='test')
    t = d.threads[0]
    assert d.last_post is not None
    assert t.last_post is not None
    t.create_post_threads(t.posts)
    posts0 = t.find_posts(page=0, limit=10, style='threaded')
    posts1 = t.find_posts(page=0, limit=10, style='timestamp')
    assert posts0 != posts1
    ts = p0.timestamp.replace(
        microsecond=int(p0.timestamp.microsecond // 1000) * 1000)
    posts2 = t.find_posts(page=0, limit=10, style='threaded', timestamp=ts)
    assert len(posts2) > 0

    assert 'wiki/_discuss/' in t.url()
    assert t.index()['views_i'] == 0
    assert not t.subscription
    t.subscription = True
    assert t.subscription
    t.subscription = False
    assert not t.subscription
    assert t.top_level_posts().count() == 2
    assert t.post_count == 3
    jsn = t.__json__()
    assert '_id' in jsn
    assert_equals(len(jsn['posts']), 3)
    (p.approve() for p in (p0, p1))
    assert t.num_replies == 2
    t.spam()
    assert t.num_replies == 0
    ThreadLocalORMSession.flush_all()
    assert len(t.find_posts()) == 0
    t.delete()

@with_setup(setUp, tearDown)
def test_post_methods():
    d = M.Discussion(shortname='test', name='test')
    t = M.Thread(discussion_id=d._id, subject='Test Thread')
    p = t.post('This is a post')
    p2 = t.post('This is another post')
    assert p.discussion_class() == M.Discussion
    assert p.thread_class() == M.Thread
    assert p.attachment_class() == M.DiscussionAttachment
    p.commit()
    assert p.parent is None
    assert p.subject == 'Test Thread'
    assert p.attachments.count() == 0
    assert 'Test Admin' in p.summary()
    assert 'wiki/_discuss' in p.url()
    assert p.reply_subject() == 'Re: Test Thread'
    assert p.link_text() == p.subject

    ss = p.history().first()
    assert 'Version' in ss.index()['title_s']
    assert '#' in ss.shorthand_id()

    jsn = p.__json__()
    assert jsn["thread_id"] == t._id

    (p.approve() for p in (p, p2))
    assert t.num_replies == 1
    p2.spam()
    assert t.num_replies == 0
    p.spam()
    assert t.num_replies == 0
    p.delete()
    assert t.num_replies == 0

@with_setup(setUp, tearDown)
def test_attachment_methods():
    d = M.Discussion(shortname='test', name='test')
    t = M.Thread(discussion_id=d._id, subject='Test Thread')
    p = t.post('This is a post')
    p_att = p.attach('foo.text', StringIO('Hello, world!'),
                discussion_id=d._id,
                thread_id=t._id,
                post_id=p._id)
    t_att = p.attach('foo2.text', StringIO('Hello, thread!'),
                discussion_id=d._id,
                thread_id=t._id)
    d_att = p.attach('foo3.text', StringIO('Hello, discussion!'),
                discussion_id=d._id)

    ThreadLocalORMSession.flush_all()
    assert p_att.post == p
    assert p_att.thread == t
    assert p_att.discussion == d
    for att in (p_att, t_att, d_att):
        assert 'wiki/_discuss' in att.url()
        assert 'attachment/' in att.url()

    # Test notification in mail
    t = M.Thread(discussion_id=d._id, subject='Test comment notification')
    fs = FieldStorage()
    fs.name='file_info'
    fs.filename='fake.txt'
    fs.type = 'text/plain'
    fs.file=StringIO('this is the content of the fake file\n')
    p = t.post(text=u'test message', forum= None, subject= '', file_info=fs)
    ThreadLocalORMSession.flush_all()
    n = M.Notification.query.get(subject=u'[test:wiki] Test comment notification')
    assert_equals(u'test message\n\n\nAttachment: fake.txt (37 Bytes; text/plain)', n.text)

@with_setup(setUp, tearDown)
def test_discussion_delete():
    d = M.Discussion(shortname='test', name='test')
    t = M.Thread(discussion_id=d._id, subject='Test Thread')
    p = t.post('This is a post')
    p.attach('foo.text', StringIO(''),
                discussion_id=d._id,
                thread_id=t._id,
                post_id=p._id)
    ThreadLocalORMSession.flush_all()
    d.delete()

@with_setup(setUp, tearDown)
def test_thread_delete():
    d = M.Discussion(shortname='test', name='test')
    t = M.Thread(discussion_id=d._id, subject='Test Thread')
    p = t.post('This is a post')
    p.attach('foo.text', StringIO(''),
                discussion_id=d._id,
                thread_id=t._id,
                post_id=p._id)
    ThreadLocalORMSession.flush_all()
    t.delete()

@with_setup(setUp, tearDown)
def test_post_delete():
    d = M.Discussion(shortname='test', name='test')
    t = M.Thread(discussion_id=d._id, subject='Test Thread')
    p = t.post('This is a post')
    p.attach('foo.text', StringIO(''),
                discussion_id=d._id,
                thread_id=t._id,
                post_id=p._id)
    ThreadLocalORMSession.flush_all()
    p.delete()

@with_setup(setUp, tearDown)
def test_post_permission_check():
    d = M.Discussion(shortname='test', name='test')
    t = M.Thread(discussion_id=d._id, subject='Test Thread')
    c.user = M.User.anonymous()
    try:
        p1 = t.post('This post will fail the check.')
        assert False, "Expected an anonymous post to fail."
    except exc.HTTPUnauthorized:
        pass
    p2 = t.post('This post will pass the check.', ignore_security=True)
