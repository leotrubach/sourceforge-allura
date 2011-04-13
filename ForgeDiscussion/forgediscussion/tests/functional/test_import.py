import os
import json
from datetime import datetime, timedelta
from nose.tools import assert_equal

import ming
from pylons import c, g

from allura import model as M
from alluratest.controller import TestController, TestRestApiBase


class TestImportController(TestRestApiBase):#TestController):

    def setUp(self):
        super(TestImportController, self).setUp()
        here_dir = os.path.dirname(__file__)
        self.app.get('/discussion/')
        self.json_text = open(here_dir + '/data/sf.json').read()

    def test_no_capability(self):
        self.set_api_ticket({'import2': 'test'})
        resp = self.api_post('/rest/p/test/discussion/perform_import',
            doc=self.json_text)
        assert resp.status_int == 403

        self.set_api_ticket({'import': 'test2'})
        resp = self.api_post('/rest/p/test/discussion/perform_import',
            doc=self.json_text)
        assert resp.status_int == 403

        self.set_api_ticket({'import': 'test'})
        resp = self.api_post('/rest/p/test/discussion/perform_import',
            doc=self.json_text)
        assert resp.status_int == 200

    def test_validate_import(self):
        r = self.api_post('/rest/p/test/discussion/validate_import',
            doc=self.json_text)
        assert not r.json['errors']

    def test_import_anon(self):
        api_ticket = M.ApiTicket(user_id=self.user._id, capabilities={'import': 'test'},
                                 expires=datetime.utcnow() + timedelta(days=1))
        ming.orm.session(api_ticket).flush()
        self.set_api_token(api_ticket)

        r = self.api_post('/rest/p/test/discussion/perform_import',
                          doc=self.json_text)
        assert not r.json['errors'], r.json['errors']
        r = self.app.get('/p/test/discussion/')
        assert 'Open Discussion:' in str(r), r.showbrowser()
        assert 'Welcome to Developers' in str(r), r.showbrowser()
        for link in r.html.findAll('a'):
            if link.string == 'Welcome to Developers': break
        r = self.app.get(link.get('href'))
        assert '2009-11-19' in str(r), r.showbrowser()
        assert 'Welcome to Developers' in str(r), r.showbrowser()
        assert 'Anonymous Coward' in str(r), r.showbrowser()

    def test_import_map(self):
        api_ticket = M.ApiTicket(user_id=self.user._id, capabilities={'import': 'test'},
                                 expires=datetime.utcnow() + timedelta(days=1))
        ming.orm.session(api_ticket).flush()
        self.set_api_token(api_ticket)

        r = self.api_post('/rest/p/test/discussion/perform_import',
                          doc=self.json_text,
                          username_mapping=json.dumps(dict(rick446='test-user')))
        assert not r.json['errors'], r.json['errors']
        r = self.app.get('/p/test/discussion/')
        assert 'Open Discussion:' in str(r), r.showbrowser()
        assert 'Welcome to Developers' in str(r), r.showbrowser()
        for link in r.html.findAll('a'):
            if link.string == 'Welcome to Developers': break
        r = self.app.get(link.get('href'))
        assert '2009-11-19' in str(r), r.showbrowser()
        assert 'Welcome to Developers' in str(r), r.showbrowser()
        assert 'Test User' in str(r), r.showbrowser()
        assert 'Anonymous Coward' not in str(r), r.showbrowser()

    def test_import_create(self):
        api_ticket = M.ApiTicket(user_id=self.user._id, capabilities={'import': 'test'},
                                 expires=datetime.utcnow() + timedelta(days=1))
        ming.orm.session(api_ticket).flush()
        self.set_api_token(api_ticket)

        r = self.api_post('/rest/p/test/discussion/perform_import',
                          doc=self.json_text, create_users=True)
        assert not r.json['errors'], r.json['errors']
        r = self.app.get('/p/test/discussion/')
        assert 'Open Discussion:' in str(r), r.showbrowser()
        assert 'Welcome to Developers' in str(r), r.showbrowser()
        for link in r.html.findAll('a'):
            if link.string == 'Welcome to Developers': break
        r = self.app.get(link.get('href'))
        assert '2009-11-19' in str(r), r.showbrowser()
        assert 'Welcome to Developers' in str(r), r.showbrowser()
        assert 'Anonymous Coward' not in str(r), r.showbrowser()
        assert 'test-rick446' in str(r), r.showbrowser()

    def set_api_ticket(self, caps={'import': 'test'}):
        api_ticket = M.ApiTicket(user_id=self.user._id, capabilities=caps,
                                 expires=datetime.utcnow() + timedelta(days=1))
        ming.orm.session(api_ticket).flush()
        self.set_api_token(api_ticket)

    @staticmethod
    def time_normalize(t):
        return t.replace('T', ' ').replace('Z', '')

    def verify_ticket(self, from_api, org):
        assert_equal(from_api['status'], org['status'])
        assert_equal(from_api['description'], org['description'])
        assert_equal(from_api['summary'], org['summary'])
        assert_equal(from_api['ticket_num'], org['id'])
        assert_equal(from_api['created_date'], self.time_normalize(org['date']))
        assert_equal(from_api['mod_date'], self.time_normalize(org['date_updated']))
        assert_equal(from_api['custom_fields']['_resolution'], org['resolution'])
        assert_equal(from_api['custom_fields']['_cc'], org['cc'])
        assert_equal(from_api['custom_fields']['_private'], org['private'])