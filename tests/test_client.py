from StringIO import StringIO
from httplib import CONFLICT, NOT_FOUND, PRECONDITION_FAILED, UNAUTHORIZED
import unittest
from datetime import datetime
import requests
from box import BoxClient, ShareAccess, EventFilter, BoxClientException, ItemAlreadyExists, ItemDoesNotExist, PreconditionFailed, BoxAccountUnauthorized, CredentialsV2, CredentialsV1
from flexmock import flexmock
from tests import FileObjMatcher, UTC, CallableMatcher
import json

class TestClient(unittest.TestCase):
    def make_client(self):
        """
        Makes a new test client
        """
        client = BoxClient('my_token')
        flexmock(client) \
            .should_receive('_handle_error') \
            .once()

        return client

    def make_response(self, content={}):
        return flexmock(ok=True, json=lambda: content)

    def test_init_with_string(self):
        flexmock(CredentialsV2)\
            .should_receive('__init__')\
            .with_args('my_token')\
            .once()

        flexmock(CredentialsV2)\
            .should_receive('headers')\
            .and_return({'Authorization': 'peanuts'})\

        client = BoxClient('my_token')
        self.assertDictEqual(client._headers, {'Authorization': 'peanuts'})

    def test_init_with_credentials_class(self):
        client = BoxClient(flexmock(headers={'hello': 'world'}))
        self.assertDictEqual(client._headers, {'hello': 'world'})

    def test_get_id(self):
        self.assertEqual('123', BoxClient._get_id(123))
        self.assertEqual('123', BoxClient._get_id('123'))
        self.assertEqual('123', BoxClient._get_id(123L))
        self.assertEqual('123', BoxClient._get_id({'id': 123}))

    def test_get_file_metadata_from_response(self):
        data = {'entries': [{'id': 1}, {'id': 2}]}
        self.assertEqual({'id': 1}, BoxClient._get_file_metadata_from_response(flexmock(json=lambda: data)))

    def test_handle_error(self):
        client = BoxClient('my_token')

        self.assertIsNone(client._handle_error(flexmock(ok=True)))

        with self.assertRaises(ItemAlreadyExists) as expected_exception:
            client._handle_error(flexmock(ok=False, status_code=CONFLICT, text='something terrible'))
        self.assertEqual('something terrible', expected_exception.exception.message)

        with self.assertRaises(ItemDoesNotExist) as expected_exception:
            client._handle_error(flexmock(ok=False, status_code=NOT_FOUND, text='something terrible'))
        self.assertEqual('something terrible', expected_exception.exception.message)

        with self.assertRaises(PreconditionFailed) as expected_exception:
            client._handle_error(flexmock(ok=False, status_code=PRECONDITION_FAILED, text='something terrible'))
        self.assertEqual('something terrible', expected_exception.exception.message)

        with self.assertRaises(BoxAccountUnauthorized) as expected_exception:
            client._handle_error(flexmock(ok=False, status_code=UNAUTHORIZED, text='something terrible'))
        self.assertEqual('something terrible', expected_exception.exception.message)

        # unknown code
        with self.assertRaises(BoxClientException) as expected_exception:
            client._handle_error(flexmock(ok=False, status_code=599, text='something terrible'))
        self.assertEqual('something terrible', expected_exception.exception.message)

    def test_get(self):
        client = BoxClient('my_token')
        expected_response = self.make_response()
        flexmock(requests) \
            .should_receive('get') \
            .with_args('https://api.box.com/2.0/foo', params={'arg': 'value'}, headers=client._headers, crap=1) \
            .and_return(expected_response) \
            .once()

        actual_response = client._get('foo', {'arg': 'value'}, crap=1)
        self.assertEqual(expected_response, actual_response)

    def test_post_dict(self):
        client = BoxClient('my_token')

        expected_data = {'arg': 'value'}
        expected_response = self.make_response()
        flexmock(requests) \
            .should_receive('post') \
            .with_args('https://api.box.com/2.0/foo',
                       CallableMatcher(lambda x: json.loads(x) == expected_data),
                       headers=client._headers,
                       crap=1) \
            .and_return(expected_response) \
            .once()

        actual_response = client._post('foo', expected_data, crap=1)
        self.assertEqual(expected_response, actual_response)

    def test_post_data(self):
        client = BoxClient('my_token')

        expected_data = 'mooooo'
        expected_response = self.make_response()
        flexmock(requests) \
            .should_receive('post') \
            .with_args('https://api.box.com/2.0/foo',
                       expected_data,
                       headers=client._headers,
                       crap=1) \
            .and_return(expected_response) \
            .once()

        actual_response = client._post('foo', expected_data, crap=1)
        self.assertEqual(expected_response, actual_response)

    def test_put_dict(self):
        client = BoxClient('my_token')

        expected_data = {'arg': 'value'}
        expected_response = self.make_response()
        flexmock(requests) \
            .should_receive('put') \
            .with_args('https://api.box.com/2.0/foo',
                       CallableMatcher(lambda x: json.loads(x) == expected_data),
                       headers=client._headers,
                       crap=1) \
            .and_return(expected_response) \
            .once()

        actual_response = client._put('foo', expected_data, crap=1)
        self.assertEqual(expected_response, actual_response)

    def test_put_data(self):
        client = BoxClient('my_token')

        expected_data = 'mooooo'
        expected_response = self.make_response()
        flexmock(requests) \
            .should_receive('put') \
            .with_args('https://api.box.com/2.0/foo',
                       expected_data,
                       headers=client._headers,
                       crap=1) \
            .and_return(expected_response) \
            .once()

        actual_response = client._put('foo', expected_data, crap=1)
        self.assertEqual(expected_response, actual_response)

    def test_delete(self):
        client = BoxClient('my_token')
        expected_headers = dict(client._headers)
        custom_headers = {'hello': 'world'}
        expected_headers.update(custom_headers)

        expected_response = self.make_response()
        flexmock(requests) \
            .should_receive('delete') \
            .with_args('https://api.box.com/2.0/foo',
                       headers=expected_headers,
                       crap=1) \
            .and_return(expected_response) \
            .once()

        actual_response = client._delete('foo', headers=custom_headers, crap=1)
        self.assertEqual(expected_response, actual_response)

        # verify headers were not modified
        self.assertDictEqual(custom_headers, {'hello': 'world'})

    def test_delete_no_headers(self):
        client = BoxClient('my_token')
        expected_headers = dict(client._headers)

        expected_response = self.make_response()
        flexmock(requests) \
            .should_receive('delete') \
            .with_args('https://api.box.com/2.0/foo',
                       headers=expected_headers,
                       crap=1) \
            .and_return(expected_response) \
            .once()

        actual_response = client._delete('foo', crap=1)
        self.assertEqual(expected_response, actual_response)


    def test_get_user_info(self):
        client = self.make_client()
        response = self.make_response({'name': 'bla'})

        flexmock(client) \
            .should_receive('_get') \
            .with_args('users/me') \
            .and_return(response) \
            .once()

        self.assertDictEqual(client.get_user_info(), {'name': 'bla'})

        client = self.make_client()
        response = self.make_response()

        flexmock(client) \
            .should_receive('_get') \
            .with_args('users/john') \
            .and_return(response) \
            .once()

        client.get_user_info('john')

    def test_get_user_list(self):
        client = self.make_client()

        response = self.make_response()
        flexmock(client) \
            .should_receive('_get') \
            .with_args('users/', query={'count': 123, 'offset': 456}) \
            .and_return(response) \
            .once()

        client.get_user_list(count=123, offset=456)

    def test_get_folder(self):
        client = self.make_client()

        response = self.make_response()
        flexmock(client) \
            .should_receive('_get') \
            .with_args('folders/666', query={'count': 123, 'offset': 456}) \
            .and_return(response) \
            .once()
        client.get_folder(folder_id=666, count=123, offset=456)

        client = self.make_client()
        flexmock(client) \
            .should_receive('_get') \
            .with_args('folders/666', query={'count': 123, 'offset': 456, 'fields': ['hello']}) \
            .and_return(response) \
            .once()
        client.get_folder(folder_id=666, count=123, offset=456, fields=['hello'])

    def test_get_folder_content(self):
        client = self.make_client()

        response = self.make_response()
        flexmock(client) \
            .should_receive('_get') \
            .with_args('folders/666/items', query={'count': 123, 'offset': 456}) \
            .and_return(response) \
            .once()
        client.get_folder_content(folder_id=666, count=123, offset=456)

        client = self.make_client()
        flexmock(client) \
            .should_receive('_get') \
            .with_args('folders/666/items', query={'count': 123, 'offset': 456, 'fields': ['hello']}) \
            .and_return(response) \
            .once()

        client.get_folder_content(folder_id=666, count=123, offset=456, fields=['hello'])


    def test_get_folder_iterator(self):
        # setup a regular client without expecting the usual calls
        client = BoxClient('my_token')
        flexmock(client) \
            .should_receive('get_folder_content') \
            .with_args(666, count=1000) \
            .and_return({'entries': range(10)}) \
            .once()

        flexmock(client) \
            .should_receive('get_folder_content') \
            .with_args(666, count=1000, offset=1000) \
            .and_return({'entries': None}) \
            .once()

        self.assertListEqual(list(client.get_folder_iterator(666)), list(range(10)))

    def test_get_folder_iterator_zero_content(self):
        # setup a regular client without expecting the usual calls
        client = BoxClient('my_token')
        flexmock(client) \
            .should_receive('get_folder_content') \
            .with_args(666, count=1000) \
            .and_return({'entries': None}) \
            .once()

        self.assertListEqual(list(client.get_folder_iterator(666)), [])

    def test_create_folder_no_parent(self):
        client = self.make_client()
        expected_dict = {
            'name': 'hello',
            'parent': {'id': '0'}
        }
        expected_result = {'entries': None}
        response = self.make_response(expected_result)

        flexmock(client) \
            .should_receive('_post') \
            .with_args('folders', expected_dict) \
            .and_return(response) \
            .once()

        result = client.create_folder(name='hello')
        self.assertEqual(result, expected_result)

    def test_create_folder_with_parent(self):
        client = self.make_client()
        expected_dict = {
            'name': 'hello',
            'parent': {'id': '123'}
        }
        expected_result = {'entries': None}
        response = self.make_response(expected_result)

        flexmock(client) \
            .should_receive('_post') \
            .with_args('folders', expected_dict) \
            .and_return(response) \
            .once()

        result = client.create_folder(name='hello', parent=123)
        self.assertEqual(result, expected_result)

    def test_get_file_metadata(self):
        client = self.make_client()

        response = self.make_response()
        flexmock(client) \
            .should_receive('_get') \
            .with_args('files/123') \
            .and_return(response) \
            .once()

        client.get_file_metadata(123)


    def test_delete_file(self):
        client = self.make_client()

        response = self.make_response()
        flexmock(client) \
            .should_receive('_delete') \
            .with_args('files/123', {}) \
            .and_return(response) \
            .once()

        client.delete_file(123)

        client = self.make_client()
        flexmock(client) \
            .should_receive('_delete') \
            .with_args('files/123', {'If-Match': 'deadbeef'}) \
            .and_return(response) \
            .once()

        client.delete_file(123, etag='deadbeef')

    def test_delete_trashed_file(self):
        client = self.make_client()

        response = self.make_response()
        flexmock(client) \
            .should_receive('_delete') \
            .with_args('files/123/trash') \
            .and_return(response) \
            .once()

        client.delete_trashed_file(123)

    def test_download_file(self):
        client = self.make_client()

        response = flexmock(ok=True, raw=StringIO('hello world'))
        flexmock(client) \
            .should_receive('_get') \
            .with_args('files/123/content', query={}, stream=True) \
            .and_return(response) \
            .once()

        downloaded_file = client.download_file(123)
        self.assertEqual('hello world', downloaded_file.read())

    def test_download_file_with_version(self):
        client = self.make_client()

        response = flexmock(ok=True, raw=StringIO('hello world'))
        flexmock(client) \
            .should_receive('_get') \
            .with_args('files/123/content', query={'version': 1000}, stream=True) \
            .and_return(response) \
            .once()

        downloaded_file = client.download_file(123, 1000)
        self.assertEqual('hello world', downloaded_file.read())

    def test_upload_file(self):
        client = self.make_client()
        response = self.make_response()
        flexmock(requests) \
            .should_receive('post') \
            .with_args('https://upload.box.com/api/2.0/files/content',
                       headers=client._headers,
                       data={'parent_id': '666'},
                       files={'hello.jpg': FileObjMatcher('hello world')}) \
            .and_return(response) \
            .once()

        flexmock(client) \
            .should_receive('_get_file_metadata_from_response') \
            .with_args(response) \
            .and_return({'id': '1'}) \
            .once()

        result = client.upload_file('hello.jpg', StringIO('hello world'), parent=666)
        self.assertEqual({'id': '1'}, result)

    def test_upload_file_with_parent_as_dict(self):
        client = self.make_client()
        response = self.make_response()
        flexmock(requests) \
            .should_receive('post') \
            .with_args('https://upload.box.com/api/2.0/files/content',
                       headers=client._headers,
                       data={'parent_id': '666'},
                       files={'hello.jpg': FileObjMatcher('hello world')}) \
            .and_return(response) \
            .once()

        flexmock(client) \
            .should_receive('_get_file_metadata_from_response') \
            .with_args(response) \
            .and_return({'id': '1'}) \
            .once()

        result = client.upload_file('hello.jpg', StringIO('hello world'), parent={'id': 666})
        self.assertEqual({'id': '1'}, result)

    def test_overwrite_file(self):
        client = self.make_client()
        expected_headers = dict(client._headers)
        expected_headers['content_modified_at'] = '2006-05-04T03:02:01+00:00'
        expected_headers['If-Match'] = 'some_tag'
        expected_response = self.make_response()

        flexmock(requests) \
            .should_receive('post') \
            .with_args('https://upload.box.com/api/2.0/files/666/content',
                       headers=expected_headers,
                       files={'file': FileObjMatcher('hello world')}) \
            .and_return(expected_response) \
            .once()

        flexmock(client) \
            .should_receive('_get_file_metadata_from_response') \
            .with_args(expected_response) \
            .and_return({'id': '1'}) \
            .once()

        result = client.overwrite_file(666, StringIO('hello world'), etag='some_tag',
                                       content_modified_at=datetime(2006, 5, 4, 3, 2, 1, 0, tzinfo=UTC()))

        self.assertEqual({'id': '1'}, result)


    def test_copy_file(self):
        expected_result = {'id': '1'}
        response = self.make_response(expected_result)
        client = self.make_client()

        # same name, different parent
        flexmock(client) \
            .should_receive('_post') \
            .with_args('files/123/copy', {'parent': {'id': '666'}}) \
            .and_return(response) \
            .once()

        result = client.copy_file(123, 666)
        self.assertEqual(expected_result, result)

        client = self.make_client()
        # different name
        flexmock(client) \
            .should_receive('_post') \
            .with_args('files/123/copy', {
            'parent': {'id': '666'},
            'name': 'goatse.cx'}) \
            .and_return(response) \
            .once()

        result = client.copy_file(123, 666, 'goatse.cx')
        self.assertEqual(expected_result, result)

    def test_share_link(self):
        response = self.make_response({'shared_link': 'http://www.foo.org/bla?x=y'})
        client = self.make_client()

        # defaults
        args = {
            'permissions': {
                'can_preview': True,
                'can_download': True,
            },
            'access': 'open'
        }

        flexmock(client) \
            .should_receive('_put') \
            .with_args('files/123', {'shared_link': args}) \
            .and_return(response) \
            .once()

        link = client.share_link(123)
        self.assertEqual('http://www.foo.org/bla?x=y', link)

        # with expiration time
        client = self.make_client()
        args = {
            'permissions': {
                'can_preview': False,
                'can_download': False,
            },
            'access': 'company',
            'unshared_at': '2006-05-04T03:02:01+00:00'
        }

        flexmock(client) \
            .should_receive('_put') \
            .with_args('files/123', {'shared_link': args}) \
            .and_return(response) \
            .once()

        link = client.share_link(123, access=ShareAccess.COMPANY,
                                 expire_at=datetime(2006, 5, 4, 3, 2, 1, 0, tzinfo=UTC()),
                                 can_download=False,
                                 can_preview=False)

        self.assertEqual('http://www.foo.org/bla?x=y', link)

    def test_get_events(self):
        response = self.make_response()
        client = self.make_client()

        # defaults
        args = {
            'stream_position': '0',
            'stream_type': 'all',
            'limit': 1000
        }

        flexmock(client) \
            .should_receive('_get') \
            .with_args('events', args) \
            .and_return(response) \
            .once()

        client.get_events()

        # custom arguments
        client = self.make_client()
        args = {
            'stream_position': '123',
            'stream_type': 'changes',
            'limit': 9
        }

        flexmock(client) \
            .should_receive('_get') \
            .with_args('events', args) \
            .and_return(response) \
            .once()

        client.get_events(stream_position=123, stream_type=EventFilter.CHANGES, limit=9)

    def test_get_path_of_file(self):
        metadata = {
            "name": "hello.jpg",
            "path_collection": {
                "total_count": 2,
                "entries": [
                    {
                        "type": "folder",
                        "id": "0",
                        "name": "All Files"
                    },
                    {
                        "type": "folder",
                        "id": "11446498",
                        "sequence_id": "1",
                        "etag": "1",
                        "name": "Pictures"
                    }
                ]
            }
        }

        self.assertEqual('/Pictures/hello.jpg', BoxClient.get_path_of_file(metadata))

        metadata = {
            "name": "hello.jpg",
            "path_collection": {
                "total_count": 2,
                "entries": [
                    {
                        "type": "folder",
                        "id": "0",
                        "name": "All Files"
                    },
                ]
            }
        }

        self.assertEqual('/hello.jpg', BoxClient.get_path_of_file(metadata))

    def test_get_long_poll_data(self):
        client = BoxClient('my_token')

        expected_response = {
            'type': 'realtime_server',
            'url': 'http://2.realtime.services.box.net/subscribe?channel=e9de49a73f0c93a872d7&stream_type=all',
            'ttl': '10',
            'max_retries': '10',
            'retry_timeout': 610
        }

        response = self.make_response({
            'chunk_size': 1,
            'entries': [expected_response],
        })

        flexmock(requests) \
            .should_receive('options') \
            .with_args('https://api.box.com/2.0/events', headers=client._headers) \
            .and_return(response) \
            .once()

        actual_response = client._get_long_poll_data()
        self.assertDictEqual(expected_response, actual_response)

    def test_long_poll_for_latest_events(self):

        for stream_position in ['now', None]:
            client = BoxClient('my_token')

            longpoll_response = {
                'type': 'realtime_server',
                'url': 'http://2.realtime.services.box.net/subscribe?channel=12345678&stream_type=all',
                'ttl': '10',
                'max_retries': '10',
                'retry_timeout': 610
            }

            expected_get_params = {
                'channel': ['12345678'],
                'stream_type': 'changes',
                'stream_position': 'some_stream_position',
            }


            flexmock(client) \
                .should_receive('_get_long_poll_data') \
                .and_return(longpoll_response) \
                .once()

            flexmock(client) \
                .should_receive('get_events') \
                .with_args(stream_position='now', stream_type=EventFilter.CHANGES) \
                .and_return({'next_stream_position': 'some_stream_position'}) \
                .once()

            flexmock(requests) \
                .should_receive('get') \
                .with_args('http://2.realtime.services.box.net/subscribe', params=expected_get_params) \
                .and_return(self.make_response(content={'message': 'new_message'})) \
                .once()


            position = client.long_poll_for_events(stream_position, stream_type=EventFilter.CHANGES)
            self.assertEqual('some_stream_position', position)

    def test_long_poll_for_events_ok(self):
        client = BoxClient('my_token')

        longpoll_response = {
            'type': 'realtime_server',
            'url': 'http://2.realtime.services.box.net/subscribe?channel=12345678&stream_type=all',
            'ttl': '10',
            'max_retries': '10',
            'retry_timeout': 610
        }

        flexmock(client) \
            .should_receive('_get_long_poll_data') \
            .and_return(longpoll_response) \
            .once()

        expected_get_params = {
            'channel': ['12345678'],
            'stream_type': 'changes',
            'stream_position': 'some_stream_position',
        }

        flexmock(requests) \
            .should_receive('get') \
            .with_args('http://2.realtime.services.box.net/subscribe', params=expected_get_params) \
            .and_return(self.make_response(content={'message': 'new_message'})) \
            .once()

        position = client.long_poll_for_events('some_stream_position', stream_type=EventFilter.CHANGES)
        self.assertEqual('some_stream_position', position)

    def test_long_poll_for_events_multiple_tries(self):
        client = BoxClient('my_token')

        longpoll_response = {
            'type': 'realtime_server',
            'url': 'http://2.realtime.services.box.net/subscribe?channel=12345678&stream_type=all',
            'ttl': '10',
            'max_retries': '10',
            'retry_timeout': 610
        }

        flexmock(client) \
            .should_receive('_get_long_poll_data') \
            .and_return(longpoll_response) \
            .times(5)

        flexmock(client) \
            .should_receive('get_events') \
            .times(0)

        expected_get_params = {
            'channel': ['12345678'],
            'stream_type': 'changes',
            'stream_position': 'some_stream_position',
        }

        flexmock(requests) \
            .should_receive('get') \
            .with_args('http://2.realtime.services.box.net/subscribe', params=expected_get_params) \
            .and_return(self.make_response(content={'message': 'foo'})) \
            .and_return(self.make_response(content={'message': 'foo'})) \
            .and_return(self.make_response(content={'message': 'foo'})) \
            .and_return(self.make_response(content={'message': 'foo'})) \
            .and_return(self.make_response({'message': 'new_message'})) \
            .times(5)

        position = client.long_poll_for_events('some_stream_position', stream_type=EventFilter.CHANGES)
        self.assertEqual('some_stream_position', position)

    def test_long_poll_for_events_and_errors(self):
        client = BoxClient('my_token')

        longpoll_response = {
            'type': 'realtime_server',
            'url': 'http://2.realtime.services.box.net/subscribe?channel=12345678&stream_type=all',
            'ttl': '10',
            'max_retries': '10',
            'retry_timeout': 610
        }

        flexmock(client) \
            .should_receive('_get_long_poll_data') \
            .and_return(longpoll_response) \
            .times(2)

        expected_get_params = {
            'channel': ['12345678'],
            'stream_type': 'changes',
            'stream_position': 'some_stream_position',
        }

        flexmock(requests) \
            .should_receive('get') \
            .with_args('http://2.realtime.services.box.net/subscribe', params=expected_get_params) \
            .and_return(self.make_response(content={'message': 'foo'})) \
            .and_return(flexmock(ok=False, text='some error', status_code=400)) \
            .times(2)

        with self.assertRaises(BoxClientException) as expect_exception:
            client.long_poll_for_events('some_stream_position', stream_type=EventFilter.CHANGES)

        self.assertEqual('some error', expect_exception.exception.message)


if __name__ == '__main__':
    unittest.main()
