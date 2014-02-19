from tests import mocked_response
import unittest2 as unittest
from urlparse import urlsplit, parse_qs

from flexmock import flexmock
import requests

from box import start_authenticate_v1, finish_authenticate_v1, \
    BoxAuthenticationException, start_authenticate_v2, finish_authenticate_v2, \
    CredentialsV1, CredentialsV2, refresh_v2_token
from box.client import _oauth2_token_request, _handle_auth_response


class TestAuthenticationV1(unittest.TestCase):

    def test_refresh(self):
        self.assertEqual(CredentialsV1("foo", "bar").refresh(), False)

    def test_start_authenticate_v1(self):
        response = mocked_response('<response><status>get_ticket_ok</status><ticket>golden_ticket</ticket></response>')
        (flexmock(requests)
            .should_receive('get')
            .with_args('https://www.box.com/api/1.0/rest?action=get_ticket&api_key=my_api_key')
            .and_return(response))

        self.assertEqual(start_authenticate_v1('my_api_key'), 'https://www.box.com/api/1.0/auth/golden_ticket')

    def test_start_authenticate_v1_fail(self):
        response = mocked_response('something_terrible', status_code=400)
        (flexmock(requests)
            .should_receive('get')
            .with_args('https://www.box.com/api/1.0/rest?action=get_ticket&api_key=my_api_key')
            .and_return(response))

        with self.assertRaises(BoxAuthenticationException) as expected_exception:
            self.assertEqual(start_authenticate_v1('my_api_key'), 'https://www.box.com/api/1.0/auth/golden_ticket')

        self.assertEqual('something_terrible', expected_exception.exception.message)

        response = mocked_response('<response><status>something_terrible</status></response>')
        (flexmock(requests)
            .should_receive('get')
            .with_args('https://www.box.com/api/1.0/rest?action=get_ticket&api_key=my_api_key')
            .and_return(response))

        with self.assertRaises(BoxAuthenticationException) as expected_exception:
            self.assertEqual(start_authenticate_v1('my_api_key'), 'https://www.box.com/api/1.0/auth/golden_ticket')

        self.assertEqual('something_terrible', expected_exception.exception.message)

    def test_finish_authenticate_v1(self):
        response = mocked_response("""<response><status>get_auth_token_ok</status>
        <auth_token>123456</auth_token>
        <user>
            <name>test_name</name>
        </user>
        </response>""")
        (flexmock(requests)
            .should_receive('get')
            .with_args('https://www.box.com/api/1.0/rest', params={
                'action': 'get_auth_token',
                'api_key': 'my_api_key',
                'ticket': 'golden_ticket'
            })
            .and_return(response))

        self.assertDictEqual(finish_authenticate_v1('my_api_key', 'golden_ticket'), {
            'token': '123456',
            'user': {
                'name': 'test_name'
            }
        })

    def test_finish_authenticate_error(self):
        response = mocked_response('something_terrible', status_code=400)
        (flexmock(requests)
            .should_receive('get')
            .with_args('https://www.box.com/api/1.0/rest', params={
                'action': 'get_auth_token',
                'api_key': 'my_api_key',
                'ticket': 'golden_ticket'
            })
            .and_return(response))

        with self.assertRaises(BoxAuthenticationException) as expected_exception:
            finish_authenticate_v1('my_api_key', 'golden_ticket')

        self.assertEqual('something_terrible', expected_exception.exception.message)

        response = mocked_response('<response><status>something_terrible</status></response>')
        (flexmock(requests)
            .should_receive('get')
            .with_args('https://www.box.com/api/1.0/rest', params={
                'action': 'get_auth_token',
                'api_key': 'my_api_key',
                'ticket': 'golden_ticket'
            })
            .and_return(response))

        with self.assertRaises(BoxAuthenticationException) as expected_exception:
            finish_authenticate_v1('my_api_key', 'golden_ticket')

        self.assertEqual('something_terrible', expected_exception.exception.message)


class RefreshCallback(object):

    def refreshed(self, access_token, refresh_token):
        pass


class TestAuthenticationV2(unittest.TestCase):

    def test_refresh(self):
        # Can never refresh without all data
        for credentials in (CredentialsV2("access_token", "refresh_token", "client_id"),
                            CredentialsV2("access_token", "refresh_token", None, "client_secret"),
                            CredentialsV2("access_token", None, "client_id", "client_secret")):
            self.assertEqual(credentials.refresh(), False)

        # With callback
        flexmock(RefreshCallback).should_receive("refreshed").with_args('new_access_token', 'new_refresh_token').once()
        credentials = CredentialsV2("access_token", "refresh_token", "111", "222", RefreshCallback().refreshed)
        args = {
            'client_id': '111',
            'client_secret': '222',
            'refresh_token': 'refresh_token',
            'grant_type': 'refresh_token',
        }
        (flexmock(requests)
            .should_receive('post')
            .with_args('https://www.box.com/api/oauth2/token', args)
            .and_return(mocked_response({'access_token': 'new_access_token',
                                         'refresh_token': 'new_refresh_token'}))
            .once())

        self.assertEqual(credentials.refresh(), True)
        self.assertEqual(credentials._access_token, 'new_access_token')
        self.assertEqual(credentials._refresh_token, 'new_refresh_token')

        # Without callback
        credentials = CredentialsV2("access_token", "refresh_token", "111", "222")
        args = {
            'client_id': '111',
            'client_secret': '222',
            'refresh_token': 'refresh_token',
            'grant_type': 'refresh_token',
        }
        (flexmock(requests)
            .should_receive('post')
            .with_args('https://www.box.com/api/oauth2/token', args)
            .and_return(mocked_response({'access_token': 'new_access_token',
                                         'refresh_token': 'new_refresh_token'}))
            .once())

        self.assertEqual(credentials.refresh(), True)
        self.assertEqual(credentials._access_token, 'new_access_token')
        self.assertEqual(credentials._refresh_token, 'new_refresh_token')

    def test_start_authenticate_v2(self):
        url = start_authenticate_v2('1111')
        self.assertTrue(url.startswith('https://www.box.com/api/oauth2/authorize?'))
        query = parse_qs(urlsplit(url).query)
        self.assertDictEqual({
            'response_type': ['code'],
            'client_id': ['1111'],
        }, query)

        url = start_authenticate_v2('1111', state='some_state')
        self.assertTrue(url.startswith('https://www.box.com/api/oauth2/authorize?'))
        query = parse_qs(urlsplit(url).query)
        self.assertDictEqual({
            'response_type': ['code'],
            'client_id': ['1111'],
            'state': ['some_state']
        }, query)

        url = start_authenticate_v2('1111', redirect_uri='https://foo.org?a=b')
        self.assertTrue(url.startswith('https://www.box.com/api/oauth2/authorize?'))
        query = parse_qs(urlsplit(url).query)
        self.assertDictEqual({
            'response_type': ['code'],
            'client_id': ['1111'],
            'redirect_uri': ['https://foo.org?a=b']
        }, query)

    def test_oauth2_token_request(self):
        expected_args = {
            'client_id': '111111',
            'client_secret': '22222',
            'grant_type': 'wish',
            'some_key': 'some_value'
        }

        fake_response = {
            'hello': 'world'
        }

        (flexmock(requests)
            .should_receive('post')
            .with_args('https://www.box.com/api/oauth2/token', expected_args)
            .and_return(flexmock(json=lambda: fake_response))
            .once())

        response = _oauth2_token_request('111111', '22222', 'wish', some_key='some_value')
        self.assertDictEqual(fake_response, response)

    def test_oauth2_token_request_error(self):
        expected_args = {
            'client_id': '111111',
            'client_secret': '22222',
            'grant_type': 'wish',
            'some_key': 'some_value'
        }

        fake_response = {
            'error': 'bigtuna',
            'error_description': 'jim'
        }

        (flexmock(requests)
            .should_receive('post')
            .with_args('https://www.box.com/api/oauth2/token', expected_args)
            .and_return(mocked_response(fake_response))
            .once())

        with self.assertRaises(BoxAuthenticationException) as expected_exception:
            _oauth2_token_request('111111', '22222', 'wish', some_key='some_value')

        self.assertEqual('jim', expected_exception.exception.message)
        self.assertEqual('bigtuna', expected_exception.exception.error)

    def test_finish_authenticate_v2(self):
        args = {
            'client_id': '111',
            'client_secret': '222',
            'code': '333',
            'grant_type': 'authorization_code',
        }

        flexmock(requests)\
            .should_receive('post')\
            .with_args('https://www.box.com/api/oauth2/token', args)\
            .and_return(flexmock(json=lambda: {'aaa': 'bbb'}))\
            .once()

        result = finish_authenticate_v2('111', '222', '333')
        self.assertDictEqual({'aaa': 'bbb'}, result)

    def test_refresh_v2_token(self):
        args = {
            'client_id': '111',
            'client_secret': '222',
            'refresh_token': '333',
            'grant_type': 'refresh_token',
        }

        (flexmock(requests)
            .should_receive('post')
            .with_args('https://www.box.com/api/oauth2/token', args)
            .and_return(flexmock(json=lambda: {'aaa': 'bbb'}))
            .once())

        result = refresh_v2_token('111', '222', '333')
        self.assertDictEqual({'aaa': 'bbb'}, result)

    def test_handle_auth_response(self):
        _handle_auth_response(mocked_response({'code': 'bla'}))
        with self.assertRaises(BoxAuthenticationException) as expected_exception:
            _handle_auth_response(mocked_response({'error': 'some_error', 'error_description': 'foobar'}))

        self.assertEqual('foobar', expected_exception.exception.message)
        self.assertEqual('some_error', expected_exception.exception.error)


class TestCredentials(unittest.TestCase):
    def test_credentials_v1(self):
        credentials = CredentialsV1('my_key', 'my_token')
        self.assertDictEqual({'Authorization': 'BoxAuth api_key=my_key&auth_token=my_token'}, credentials.headers)

    def test_credentials_v2(self):
        credentials = CredentialsV2('my_token')
        self.assertDictEqual({'Authorization': 'Bearer my_token'}, credentials.headers)

if __name__ == '__main__':
    unittest.main()
