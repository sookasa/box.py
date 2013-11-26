from StringIO import StringIO
from datetime import datetime
from httplib import CONFLICT, NOT_FOUND, PRECONDITION_FAILED, UNAUTHORIZED
import json
from tests import FileObjMatcher, UTC
import unittest

from box import BoxClient, ShareAccess, EventFilter, BoxClientException, \
    ItemAlreadyExists, ItemDoesNotExist, PreconditionFailed, BoxAccountUnauthorized, \
    CredentialsV2
from flexmock import flexmock
import requests


class TestClient(unittest.TestCase):
    def make_client(self, method, path, params=None, data=None, headers=None, endpoint="api", result=None, **kwargs):
        """
        Makes a new test client
        """
        client = BoxClient('my_token')
        flexmock(client) \
            .should_receive('_process_response') \
            .and_return(result) \
            .once()

        if headers:
            headers = dict(headers)
            headers.update(client.default_headers)
        else:
            headers = client.default_headers

        flexmock(requests) \
            .should_receive('request') \
            .with_args(method,
                       'https://%s.box.com/2.0/%s' % (endpoint, path),
                       params=params,
                       data=json.dumps(data) if isinstance(data, dict) else data,
                       headers=headers,
                       **kwargs) \
            .and_return(self.make_response(result)) \
            .once()

        return client

    def make_response(self, content=None):
        return flexmock(ok=True, status_code=200, json=lambda: content)

    def test_init_with_string(self):
        flexmock(CredentialsV2)\
            .should_receive('__init__')\
            .with_args('my_token')\
            .once()

        flexmock(CredentialsV2)\
            .should_receive('headers')\
            .and_return({'Authorization': 'peanuts'})\

        client = BoxClient('my_token')
        self.assertDictEqual(client.default_headers, {'Authorization': 'peanuts'})

    def test_init_with_credentials_class(self):
        client = BoxClient(flexmock(headers={'hello': 'world'}))
        self.assertDictEqual(client.default_headers, {'hello': 'world'})

    def test_get_id(self):
        self.assertEqual('123', BoxClient._get_id(123))
        self.assertEqual('123', BoxClient._get_id('123'))
        self.assertEqual('123', BoxClient._get_id(123L))
        self.assertEqual('123', BoxClient._get_id({'id': 123}))

    def test_handle_error(self):
        client = BoxClient('my_token')

        self.assertIsNone(client._process_response(self.make_response()))

        with self.assertRaises(ItemAlreadyExists) as expected_exception:
            client._process_response(flexmock(ok=False, status_code=CONFLICT, text='something terrible'))
        self.assertEqual(CONFLICT, expected_exception.exception.status_code)
        self.assertEqual('something terrible', expected_exception.exception.message)

        with self.assertRaises(ItemDoesNotExist) as expected_exception:
            client._process_response(flexmock(ok=False, status_code=NOT_FOUND, text='something terrible'))
        self.assertEqual(NOT_FOUND, expected_exception.exception.status_code)
        self.assertEqual('something terrible', expected_exception.exception.message)

        with self.assertRaises(PreconditionFailed) as expected_exception:
            client._process_response(flexmock(ok=False, status_code=PRECONDITION_FAILED, text='something terrible'))
        self.assertEqual(PRECONDITION_FAILED, expected_exception.exception.status_code)
        self.assertEqual('something terrible', expected_exception.exception.message)

        with self.assertRaises(BoxAccountUnauthorized) as expected_exception:
            client._process_response(flexmock(ok=False, status_code=UNAUTHORIZED, text='something terrible'))
        self.assertEqual(UNAUTHORIZED, expected_exception.exception.status_code)
        self.assertEqual('something terrible', expected_exception.exception.message)

        # unknown code
        with self.assertRaises(BoxClientException) as expected_exception:
            client._process_response(flexmock(ok=False, status_code=599, text='something terrible'))
        self.assertEqual(599, expected_exception.exception.status_code)
        self.assertEqual('something terrible', expected_exception.exception.message)

    def test_get(self):
        client = self.make_client("get", "foo", params={'arg': 'value'}, crap=1)
        client._get('foo', {'arg': 'value'}, crap=1)

    def test_post_dict(self):
        expected_data = {'arg': 'value'}
        client = self.make_client("post", "foo", data=expected_data, crap=1)

        actual_response = client._post('foo', expected_data, crap=1)
        self.assertEqual(None, actual_response)

    def test_post_data(self):
        expected_data = "mooooo"
        client = self.make_client("post", "foo", data=expected_data, crap=1)
        actual_response = client._post('foo', expected_data, crap=1)
        self.assertEqual(None, actual_response)

    def test_put_dict(self):
        expected_data = {'arg': 'value'}
        client = self.make_client("put", "foo", data=expected_data, crap=1)
        actual_response = client._put('foo', expected_data, crap=1)
        self.assertEqual(None, actual_response)

    def test_put_data(self):
        expected_data = 'mooooo'
        client = self.make_client("put", "foo", data=expected_data, crap=1)
        actual_response = client._put('foo', expected_data, crap=1)
        self.assertEqual(None, actual_response)

    def test_delete(self):
        custom_headers = {'hello': 'world'}

        client = self.make_client("delete", "foo", headers=custom_headers, crap=1)
        actual_response = client._delete('foo', headers=custom_headers, crap=1)
        self.assertEqual(None, actual_response)

        # verify headers were not modified
        self.assertDictEqual(custom_headers, {'hello': 'world'})

    def test_delete_no_headers(self):
        client = self.make_client("delete", "foo", crap=1)
        actual_response = client._delete('foo', crap=1)
        self.assertEqual(None, actual_response)


    def test_get_user_info(self):
        client = self.make_client("get", 'users/me', result={'name': 'bla'})

        result = client.get_user_info()
        self.assertDictEqual(result, {'name': 'bla'})

        client = self.make_client("get", 'users/john')
        client.get_user_info('john')

    def test_get_user_list(self):
        client = self.make_client("get", "users/", params={'limit': 123, 'offset': 456})
        client.get_user_list(limit=123, offset=456)

    def test_get_folder(self):
        client = self.make_client("get", 'folders/666', params={'limit': 123, 'offset': 456})
        client.get_folder(folder_id=666, limit=123, offset=456)

        client = self.make_client("get", 'folders/666', params={'limit': 123, 'offset': 456, 'fields': ['hello']})
        client.get_folder(folder_id=666, limit=123, offset=456, fields=['hello'])

    def test_get_folder_content(self):
        client = self.make_client("get", 'folders/666/items', params={'limit': 123, 'offset': 456})
        client.get_folder_content(folder_id=666, limit=123, offset=456)

        client = self.make_client("get", 'folders/666/items', params={'limit': 123, 'offset': 456, 'fields': ['hello']})
        client.get_folder_content(folder_id=666, limit=123, offset=456, fields=['hello'])

    def test_get_folder_iterator(self):
        # setup a regular client without expecting the usual calls
        client = BoxClient('my_token')
        flexmock(client) \
            .should_receive('get_folder_content') \
            .with_args(666, limit=1000) \
            .and_return({'entries': range(10)}) \
            .once()

        flexmock(client) \
            .should_receive('get_folder_content') \
            .with_args(666, limit=1000, offset=1000) \
            .and_return({'entries': None}) \
            .once()

        self.assertListEqual(list(client.get_folder_iterator(666)), list(range(10)))

    def test_get_folder_iterator_zero_content(self):
        # setup a regular client without expecting the usual calls
        client = BoxClient('my_token')
        flexmock(client) \
            .should_receive('get_folder_content') \
            .with_args(666, limit=1000) \
            .and_return({'entries': None}) \
            .once()

        self.assertListEqual(list(client.get_folder_iterator(666)), [])

    def test_create_folder_no_parent(self):
        expected_dict = {
            'name': 'hello',
            'parent': {'id': '0'}
        }
        expected_result = {'entries': None}
        client = self.make_client("post", "folders", data=expected_dict, result=expected_result)
        result = client.create_folder(name='hello')
        self.assertEqual(result, expected_result)

    def test_create_folder_with_parent(self):
        expected_dict = {
            'name': 'hello',
            'parent': {'id': '123'}
        }
        expected_result = {'entries': None}
        client = self.make_client("post", "folders", data=expected_dict, result=expected_result)
        result = client.create_folder(name='hello', parent=123)
        self.assertEqual(result, expected_result)

    def test_get_file_metadata(self):
        client = self.make_client("get", 'files/123')
        client.get_file_metadata(123)


    def test_delete_file(self):
        client = self.make_client("delete", 'files/123')
        result = client.delete_file(123)
        self.assertIsNone(result)

        client = self.make_client("delete", 'files/123', headers={'If-Match': 'deadbeef'})
        result = client.delete_file(123, etag='deadbeef')
        self.assertIsNone(result)

    def test_delete_trashed_file(self):
        client = self.make_client("delete", 'files/123/trash')

        result = client.delete_trashed_file(123)
        self.assertIsNone(result)

    def test_download_file(self):
        client = self.make_client("get", "files/123/content", params={}, result=StringIO('hello world'), stream=True)
        downloaded_file = client.download_file(123)
        self.assertEqual('hello world', downloaded_file.read())

    def test_download_file_with_version(self):
        client = self.make_client("get", "files/123/content", params={'version': 1000}, result=StringIO('hello world'), stream=True)
        downloaded_file = client.download_file(123, 1000)
        self.assertEqual('hello world', downloaded_file.read())

    def test_get_thumbnail_on_url(self):
        client = BoxClient("my_token")

        flexmock(requests) \
            .should_receive('request') \
            .with_args("get",
                       'https://api.box.com/2.0/files/123/thumbnail.png',
                       params={},
                       data=None,
                       headers=client.default_headers) \
            .and_return(self.make_response(status_code=202, headers={"Location": "http://box.com"})) \
            .once()

        thumbnail_url = client.get_thumbnail_url(123)
        self.assertEqual("http://box.com", thumbnail_url)

    def test_upload_file(self):
        client = self.make_client("post", "files/content", endpoint="upload", data={'parent_id': '666'}, files={'hello.jpg': FileObjMatcher('hello world')},
                                  result={"entries": [{"id": "1"}]})
        result = client.upload_file('hello.jpg', StringIO('hello world'), parent=666)
        self.assertEqual({'id': '1'}, result)

    def test_upload_file_with_parent_as_dict(self):
        client = self.make_client("post", "files/content", data={'parent_id': '666'},
                                  files={'hello.jpg': FileObjMatcher('hello world')}, result={"entries": [{"id": "1"}]}, endpoint="upload")
        result = client.upload_file('hello.jpg', StringIO('hello world'), parent={'id': 666})
        self.assertEqual({'id': '1'}, result)

    def test_overwrite_file(self):
        expected_headers = {'content_modified_at': '2006-05-04T03:02:01+00:00',
                            'If-Match': 'some_tag'}

        client = self.make_client("post", "files/666/content", headers=expected_headers, files={'file': FileObjMatcher('hello world')}, endpoint="upload", result={"entries": [{"id": "1"}]})
        result = client.overwrite_file(666, StringIO('hello world'), etag='some_tag',
                                       content_modified_at=datetime(2006, 5, 4, 3, 2, 1, 0, tzinfo=UTC()))
        self.assertEqual({'id': '1'}, result)


    def test_copy_file(self):
        client = self.make_client("post", 'files/123/copy', data={'parent': {'id': '666'}}, result={'id': '1'})
        result = client.copy_file(123, 666)
        self.assertEqual({'id': '1'}, result)

        client = self.make_client("post", 'files/123/copy', data={'parent': {'id': '666'}, 'name': 'goatse.cx'}, result={'id': '1'})
        result = client.copy_file(123, 666, 'goatse.cx')
        self.assertEqual({'id': '1'}, result)

    def test_share_link(self):
        # defaults
        args = {
            'permissions': {
                'can_preview': True,
                'can_download': True,
            },
            'access': 'open'
        }

        client = self.make_client("put", "files/123", data={'shared_link': args}, result={'shared_link': 'http://www.foo.org/bla?x=y'})
        link = client.share_link(123)
        self.assertEqual('http://www.foo.org/bla?x=y', link)

        # with expiration time
        args = {
            'permissions': {
                'can_preview': False,
                'can_download': False,
            },
            'access': 'company',
            'unshared_at': '2006-05-04T03:02:01+00:00'
        }
        client = self.make_client("put", "files/123", data={'shared_link': args}, result={'shared_link': 'http://www.foo.org/bla?x=y'})
        link = client.share_link(123, access=ShareAccess.COMPANY,
                                 expire_at=datetime(2006, 5, 4, 3, 2, 1, 0, tzinfo=UTC()),
                                 can_download=False,
                                 can_preview=False)
        self.assertEqual('http://www.foo.org/bla?x=y', link)

    def test_get_events(self):
        # defaults
        args = {
            'stream_position': '0',
            'stream_type': 'all',
            'limit': 1000
        }

        client = self.make_client("get", "events", params=args)
        client.get_events()

        # custom arguments
        args = {
            'stream_position': '123',
            'stream_type': 'changes',
            'limit': 9
        }
        client = self.make_client("get", "events", params=args)
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
            .should_receive('request') \
            .with_args('options', 'https://api.box.com/2.0/events', headers=client.default_headers, data=None, params=None) \
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

        self.assertEqual(400, expect_exception.exception.status_code)
        self.assertEqual('some error', expect_exception.exception.message)

    def test_search(self):
        expected_result = {"total_count": 4}
        client = self.make_client("get", "search", params={'query': "foobar", 'limit': 123, 'offset': 456}, result=expected_result)
        result = client.search("foobar", limit=123, offset=456)
        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()
