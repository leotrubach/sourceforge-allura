from urlparse import urlparse, parse_qs

from allura.tests import TestController
import allura.lib.gravatar as gravatar


class TestGravatar(TestController):

    def test_id(self):
        email = 'Wolf@example.com'
        expected_id = 'd3514940ac1b2051c8aa42970d17e3fe'
        actual_id = gravatar.id(email)
        assert expected_id == actual_id

    def test_unicode_id(self):
        email = u'Vin\u00EDcius@example.com'
        expected_id = 'e00968255d68523b034a6a39c522efdb'
        actual_id = gravatar.id(email)
        assert expected_id == actual_id, 'Expected gravitar ID %s, got %s' % (repr(expected_id), repr(actual_id))

    def test_url(self):
        email = 'Wolf@example.com'
        expected_id = 'd3514940ac1b2051c8aa42970d17e3fe'
        url = urlparse(gravatar.url(email=email))
        assert url.netloc == 'secure.gravatar.com'
        assert url.path == '/avatar/' + expected_id

    def test_defaults(self):
        email = 'Wolf@example.com'
        url = urlparse(gravatar.url(email=email, rating='x'))
        query = parse_qs(url.query)
        assert 'r' not in query
        assert query['rating'] == ['x']
