import unittest
from box import get_auth_url_v1, finish_authenticate, BoxAuthenticationException
import requests
from flexmock import flexmock

class TestAuthentication(unittest.TestCase):
    def test_get_auth_url_v1(self):
        response = flexmock(ok=True, text='<response><status>get_ticket_ok</status><ticket>golden_ticket</ticket></response>')
        flexmock(requests)\
            .should_receive('get')\
            .with_args('https://www.box.com/api/1.0/rest?action=get_ticket&api_key=my_api_key')\
            .and_return(response)

        self.assertEqual(get_auth_url_v1('my_api_key'), 'https://www.box.com/api/1.0/auth/golden_ticket')

    def test_get_auth_url_v1_fail(self):
        response = flexmock(ok=False, text='something_terrible')
        flexmock(requests)\
            .should_receive('get')\
            .with_args('https://www.box.com/api/1.0/rest?action=get_ticket&api_key=my_api_key')\
            .and_return(response)

        with self.assertRaises(BoxAuthenticationException) as expected_exception:
            self.assertEqual(get_auth_url_v1('my_api_key'), 'https://www.box.com/api/1.0/auth/golden_ticket')

        self.assertEqual('something_terrible', expected_exception.exception.message)


        response = flexmock(ok=True, text='<response><status>something_terrible</status></response>')
        flexmock(requests)\
            .should_receive('get')\
            .with_args('https://www.box.com/api/1.0/rest?action=get_ticket&api_key=my_api_key')\
            .and_return(response)

        with self.assertRaises(BoxAuthenticationException) as expected_exception:
            self.assertEqual(get_auth_url_v1('my_api_key'), 'https://www.box.com/api/1.0/auth/golden_ticket')

        self.assertEqual('something_terrible', expected_exception.exception.message)

    def test_finish_authenticate(self):
        response = flexmock(ok=True, text="""<response><status>get_auth_token_ok</status>
        <auth_token>123456</auth_token>
        <user>
            <name>test_name</name>
        </user>
        </response>""")
        flexmock(requests)\
            .should_receive('get')\
            .with_args('https://www.box.com/api/1.0/rest', params={
                'action': 'get_auth_token',
                'api_key': 'my_api_key',
                'ticket': 'golden_ticket'
            })\
            .and_return(response)

        self.assertDictEqual(finish_authenticate('my_api_key', 'golden_ticket'), {
            'token': '123456',
            'user': {
                'name': 'test_name'
            }
        })

    def test_finish_authenticate_error(self):
        response = flexmock(ok=False, text='something_terrible')
        flexmock(requests)\
            .should_receive('get')\
            .with_args('https://www.box.com/api/1.0/rest', params={
                'action': 'get_auth_token',
                'api_key': 'my_api_key',
                'ticket': 'golden_ticket'
            })\
            .and_return(response)

        with self.assertRaises(BoxAuthenticationException) as expected_exception:
            finish_authenticate('my_api_key', 'golden_ticket')

        self.assertEqual('something_terrible', expected_exception.exception.message)

        response = flexmock(ok=True, text='<response><status>something_terrible</status></response>')
        flexmock(requests)\
            .should_receive('get')\
            .with_args('https://www.box.com/api/1.0/rest', params={
                'action': 'get_auth_token',
                'api_key': 'my_api_key',
                'ticket': 'golden_ticket'
            })\
            .and_return(response)

        with self.assertRaises(BoxAuthenticationException) as expected_exception:
            finish_authenticate('my_api_key', 'golden_ticket')

        self.assertEqual('something_terrible', expected_exception.exception.message)

if __name__ == '__main__':
    unittest.main()
