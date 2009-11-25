import difflib
from pprint import pformat

import pkg_resources
from pylons import c, request
from tg import expose, redirect, validate
from formencode import validators as V

from pyforge.app import Application, ConfigOption
from pyforge.lib.dispatch import _dispatch

from helloforge import model as M
from helloforge import version

class HelloForgeApp(Application):
    '''This is the HelloWorld application for PyForge, showing
    all the rich, creamy goodness that is installable apps.
    '''
    __version__ = version.__version__
    config_options = Application.config_options + [
        ConfigOption('project_name', str, 'pname'),
        ConfigOption('message', str, 'Custom message goes here') ]
    permissions = [ 'read', 'create', 'edit', 'delete', 'comment' ]

    def __init__(self, project, config):
        Application.__init__(self, project, config)
        self.root = RootController()

    @property
    def templates(self):
        return pkg_resources.resource_filename('helloforge', 'templates')

    def install(self, project):
        self.config.options['project_name'] = project._id
        self.uninstall(project)
        p = M.Page.upsert('Root')
        p.text = 'This is the root page.'
        p.commit()

    def uninstall(self, project):
        M.Page.m.remove(dict(project_id=c.project._id))
        M.Comment.m.remove(dict(project_id=c.project._id))

class RootController(object):

    @expose('helloforge.templates.index')
    def index(self):
        return dict(message=c.app.config.options['message'])

    def _dispatch(self, state, remainder):
        return _dispatch(self, state, remainder)
        
    def _lookup(self, pname, *remainder):
        return PageController(pname), remainder

class PageController(object):

    def __init__(self, title):
        self.title = title
        self.comments = CommentController(self.page())

    def page(self, version=None):
        if version is None:
            return M.Page.upsert(self.title)
        else:
            try:
                return M.Page.upsert(self.title, version=int(version))
            except ValueError:
                return None

    @expose('helloforge.templates.page_view')
    @validate(dict(version=V.Int()))
    def index(self, version=None):
        page = self.page(version)
        if page is None:
            if version: redirect('.?version=%d' % (version-1))
            else: redirect('.')
        cur = page.version - 1
        if cur > 0: prev = cur-1
        else: prev = None
        next = cur+1
        return dict(page=self.page(version),
                    cur=cur, prev=prev, next=next)

    @expose('helloforge.templates.page_edit')
    def edit(self):
        return dict(page=self.page())

    @expose('helloforge.templates.page_history')
    def history(self):
        pages = self.page().history()
        return dict(title=self.title, pages=pages)

    @expose('helloforge.templates.page_diff')
    def diff(self, v1, v2):
        p1 = self.page(int(v1))
        p2 = self.page(int(v2))
        p1.version -= 1
        p2.version -= 1
        t1 = p1.text
        t2 = p2.text
        differ = difflib.SequenceMatcher(None, p1.text, p2.text)
        result = []
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag in ('delete', 'replace'):
                result += [ '<del>', t1[i1:i2], '</del>' ]
            if tag in ('insert', 'replace'):
                result += [ '<ins>', t2[j1:j2], '</ins>' ]
            if tag == 'equal':
                result += t1[i1:i2]
        result = ''.join(result).replace('\n', '<br/>\n')
        return dict(p1=p1, p2=p2, edits=result)
            
        p1_lines = p1.text.splitlines(True)
        p2_lines = p2.text.splitlines(True)
        hdiff=difflib.HtmlDiff()
        tbl = hdiff.make_table(
            p1_lines, p2_lines,
            '<a href=".?version=%s">Version %s</a>' % (v1, v1),
            '<a href=".?version=%s">Version %s</a>' % (v2, v2),
            context=False,
            numlines=2)
        return dict(p1=p1, p2=p2, tbl=tbl)

    @expose(content_type='text/plain')
    def raw(self):
        return pformat(self.page())

    @expose()
    def revert(self, version):
        orig = self.page(version)
        current = self.page()
        current.text = orig.text
        current.commit()
        redirect('.')

    @expose()
    def update(self, text):
        page = self.page()
        page.text = text
        page.commit()
        redirect('.')

class CommentController(object):

    def __init__(self, page, comment_id=None):
        self.page = page
        self.comment_id = comment_id

    def comment(self):
        return M.Comment.m.get(_id=self.comment_id)

    @expose()
    def reply(self, text):
        if self.comment_id:
            c = self.comment().reply()
            c.text = text
        else:
            c = self.page.reply()
            c.text = text
        c.m.save()
        redirect(request.referer)

    @expose()
    def delete(self):
        self.comment().m.delete()
        redirect(request.referer)

    def _dispatch(self, state, remainder):
        return _dispatch(self, state, remainder)
        
    def _lookup(self, next, *remainder):
        if self.comment_id:
            return CommentController(
                self.page,
                self.comment_id + '/' + next), remainder
        else:
            return CommentController(
                self.page, next), remainder

    
