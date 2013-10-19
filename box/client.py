"""
A client library for working with Box's v2 API.
For extended specs, see: http://developers.box.com/docs/
"""

from httplib import NOT_FOUND, PRECONDITION_FAILED, CONFLICT, UNAUTHORIZED
import json
import urlparse
import requests
from lxml import objectify
from os import path


class EventFilter(object):
    """
    Types of events you can fetch
    """
    ALL = 'all'
    CHANGES = 'changes'
    SYNC = 'sync'


class EventType(object):
    ITEM_CREATE = 'ITEM_CREATE'
    ITEM_UPLOAD = 'ITEM_UPLOAD'
    ITEM_MOVE = 'ITEM_MOVE'
    ITEM_COPY = 'ITEM_COPY'
    ITEM_TRASH = 'ITEM_TRASH'


class ShareAccess(object):
    OPEN = 'open'
    COMPANY = 'company'
    COLLABORATORS = 'collaborators'


def get_auth_url_v1(api_key):
    """
    Returns a url to redirect the client to. Expires after 10 minutes.
    """
    r = requests.get('https://www.box.com/api/1.0/rest?action=get_ticket&api_key=%s' % api_key)
    if not r.ok:
        raise BoxAuthenticationException(r.text)

    content = objectify.fromstring(str(r.text))
    if content.status != 'get_ticket_ok':
        raise BoxAuthenticationException(content.status.text)

    return 'https://www.box.com/api/1.0/auth/%s' % content.ticket


def finish_authenticate(api_key, ticket):
    """
    Exchanges the ticket for an auth token. Should be called after the redirect completes.
    Returns a dictionary with the token and some additional user info

    Examples output:
    {   'token': 'xbfe79wdedb5mxxxxxxxxxxxxxxxxxxx',
        'user': {
            'access_id': 123456789,
            'email': 'someuser@sookasa.com',
            'login': 'someuser@sookasa.com',
            'max_upload_size': 2147483648,
            'sharing_disabled': u'',
            'space_amount': 5368709120,
            'space_used': 2445159,
            'user_id': 987654321
        }
    }

    """
    r = requests.get('https://www.box.com/api/1.0/rest', params={'action': 'get_auth_token',
                                                                 'api_key': api_key,
                                                                 'ticket': ticket})
    if not r.ok:
        raise BoxAuthenticationException(r.text)

    content = objectify.fromstring(str(r.text))
    if content.status != 'get_auth_token_ok':
        raise BoxAuthenticationException(content.status.text)

    return {
        'token': content.auth_token.text,
        'user': {x.tag: x.pyval for x in content.user.iterchildren()}
    }


class BoxClient(object):
    def __init__(self, api_key, token):
        self._api_key = api_key
        self._token = token
        self._headers = {'Authorization': 'BoxAuth api_key=%s&auth_token=%s' % (self._api_key, self._token)}

    def _handle_error(self, response, object_id=None):
        if response.ok:
            return

        all_exceptions = {
            CONFLICT: ItemAlreadyExists,
            NOT_FOUND: ItemDoesNotExist,
            PRECONDITION_FAILED: PreconditionFailed,
            UNAUTHORIZED: BoxAccountUnauthorized
        }

        exception = all_exceptions.get(response.status_code)
        if not exception:
            exception = BoxClientException

        raise exception(response.text, response.status_code, object_id)

    def _get(self, resource, query=None, **kwargs):
        return requests.get('https://api.box.com/2.0/' + resource, params=query, headers=self._headers, **kwargs)

    def _post(self, resource, data=None, **kwargs):
        if isinstance(data, dict):
            data = json.dumps(data)

        return requests.post('https://api.box.com/2.0/' + resource, data, headers=self._headers, **kwargs)

    def _put(self, resource, data=None, **kwargs):
        if isinstance(data, dict):
            data = json.dumps(data)

        return requests.put('https://api.box.com/2.0/' + resource, data, headers=self._headers, **kwargs)

    def _delete(self, resource, headers=None, **kwargs):
        if headers:
            headers = dict(headers)
            headers.update(self._headers)
        else:
            headers = self._headers

        return requests.delete('https://api.box.com/2.0/' + resource, headers=headers, **kwargs)

    @classmethod
    def _get_id(cls, identifier):
        """
        converts a an identifier to a string id
        Args:
            - identifier: a dictionary or string or long
        """
        if isinstance(identifier, dict):
            identifier = identifier['id']

        return str(identifier)

    @classmethod
    def _get_file_metadata_from_response(self, response):
        """
        helper method - returns a the file metadata buried inside the response
        """
        return response.json()['entries'][0]

    def get_user_info(self, username=None):
        """
        Returns info.

        Args:
            - username: The username to query. If None then the info on the current user will
                        be returned

        """
        username = username or 'me'
        response = self._get('users/' + username)
        self._handle_error(response)

        return response

    def get_user_list(self, count=100, offset=0):
        """
        Returns users in an enterprise.

        Args:
            - count: number of users to return. (default=100, max=1000). Optional.
            - offset: The record at which to start. Optional.
        """

        params = {
            'count': count,
            'offset': offset,
        }

        response = self._get('users/', params)
        self._handle_error(response)

        return response.json()

    def get_folder(self, folder_id, count=100, offset=0, fields=None):
        """
        Retrieves the metadata of a folder and child directory/files.

        Args:
            - count: (optional) number of items to return. (default=100, max=1000).
            - offset: (optional) The record at which to start
            - fields: (optional) Attribute(s) to include in the response
        """

        params = {
            'count': count,
            'offset': offset,
        }

        if fields:
            params['fields'] = fields

        response = self._get('folders/{}'.format(folder_id), params)
        self._handle_error(response, folder_id)

        return response.json()

    def get_folder_content(self, folder_id, count=100, offset=0, fields=None):
        """
        Retrieves the files and/or folders contained within this folder without any other metadata about the folder.

        Args:
            - count: (optional) number of items to return. (default=100, max=1000).
            - offset: (optional) The record at which to start
            - fields: (optional) Attribute(s) to include in the response
        """

        params = {
            'count': count,
            'offset': offset,
        }

        if fields:
            params['fields'] = fields

        response = self._get('folders/{}/items'.format(folder_id), params)
        self._handle_error(response, folder_id)

        return response.json()

    def get_folder_iterator(self, folder_id):
        """
        returns an iterator over the folder entries.
        this is equivalent of iterating over the folder pages manually
        """

        batch_size = 1000
        content = self.get_folder_content(folder_id, count=batch_size)
        offset = 0
        while content['entries']:
            for entry in content['entries']:
                yield entry

            offset += batch_size
            content = self.get_folder_content(folder_id, count=batch_size, offset=offset)

    def create_folder(self, name, parent=0):
        """
        creates a new folder under the parent.

        Args:
            - parent: (optional) ID or a Dictionary (as returned by the apis) of the parent folder
        """
        args = {"name": name}
        args['parent'] = {'id': self._get_id(parent)}

        response = self._post('folders', args)
        self._handle_error(response)

    def get_file_metadata(self, file_id):
        """
        Fetches the metadata of the given file_id

        Args:
            - file_id: the file id.

        Returns a dictionary with all of the file metadata.
        """
        response = self._get('files/{}'.format(file_id))
        self._handle_error(response)

        return response.json()

    def delete_file(self, file_id, etag=None):
        """
        Discards a file to the trash.

        Args:
            - etag: (optional) If specified, the file will only be deleted if
                    its etag matches the parameter
        """

        headers = {}
        if etag:
            headers['If-Match'] = etag

        response = self._delete('files/{}'.format(file_id), headers)
        self._handle_error(response, file_id)

        return response

    def delete_trashed_file(self, file_id):
        """
        Permanently deletes an item that is in the trash.
        """
        response = self._delete('files/{}/trash'.format(file_id))
        self._handle_error(response, file_id)

        return response

    def download_file(self, file_id, version=None):
        """
        Downloads a file

        Args:
            - file_id: The ID of the file to download.
            - version: (optional) The ID specific version of this file to download.

        Returns a file-like object to the file content
        """

        query = {}
        if version:
            query['version'] = version

        response = self._get('files/{}/content'.format(file_id), query=query, stream=True)
        self._handle_error(response)
        return response.raw

    def upload_file(self, filename, fileobj, parent=0):
        """
        Uploads a file. If the file already exists, ItemAlreadyExists is raised.

        Args:
            - filename: the filename to be used. If the file already exists, an ItemAlreadyExists exception will be
                        raised.
            - fileobj: a fileobj-like object that contains the data to upload
            - parent: (optional) ID or a Dictionary (as returned by the apis) of the parent folder
        """

        form = {"parent_id": self._get_id(parent)}

        # usually Box goes with data==json, but here they want headers (as per standard http form)
        response = requests.post('https://upload.box.com/api/2.0/files/content',
                                 headers=self._headers,
                                 data=form,
                                 files={filename: fileobj})

        self._handle_error(response, filename)
        return self._get_file_metadata_from_response(response)

    def overwrite_file(self, file_id, fileobj, etag=None, content_modified_at=None):
        """
        Uploads a file that will overwrite an existing one. The file_id must exist on the server.
        """
        headers = dict(self._headers)
        if etag:
            headers['If-Match'] = etag

        if content_modified_at:
            headers['content_modified_at'] = content_modified_at.isoformat()

        response = requests.post('https://upload.box.com/api/2.0/files/{}/content'.format(file_id),
                                 headers=headers,
                                 files={'file': fileobj})

        self._handle_error(response, file_id)
        return self._get_file_metadata_from_response(response)

    def copy_file(self, file_id, destination_parent, new_filename=None):
        """
        Copies a file

        Args:
            - file_id: the id of the file we want to copy
            - destination_parent: ID or a dictionary (as returned by the apis) of the parent folder
            - new_filename: (optional) the new filename to use. If not passed, the original filename will be used.

        Returns:
            - a dictionary with the new file metadata
        """

        args = {'parent': {'id': self._get_id(destination_parent)}}
        if new_filename:
            args['name'] = new_filename

        response = self._post('files/{}/copy'.format(file_id), args)
        self._handle_error(response, file_id)

        return response

    def share_link(self, file_id, access=ShareAccess.OPEN, expire_at=None, can_download=True, can_preview=True):
        """
        Creates a share link for the file_id
        Args:
            - file_id: the id of the file we want to share
            - access: one of the values of ShareAccess
            - expire_at: (optional) a datetime representing the time the link will expire. Timestamps are rounded off
              to the given day.
            - can_download: allows downloading of the file.
            - can_preview: allows the file to the previewed.

        Returns:
            - a dictionary containing the various urls. Example:
            {
                 "url": "https://www.box.com/s/rh935iit6ewrmw0unyul",
                "download_url": "https://www.box.com/shared/static/rh935iit6ewrmw0unyul.jpeg",
                "vanity_url": null,
                "is_password_enabled": false,
                "unshared_at": null,
                "download_count": 0,
                "preview_count": 0,
                "access": "open",
                "permissions": {
                    "can_download": true,
                    "can_preview": true
                }
            }
        """
        args = {
            'access': access,
            'permissions': {'can_download': can_download,
                            'can_preview': can_preview
                            }
        }

        if expire_at:
            args['unshared_at'] = expire_at.isoformat()

        response = self._put('files/{}'.format(file_id), {'shared_link': args})
        self._handle_error(response, file_id)

        return response.json()['shared_link']

    def get_events(self, stream_position='0', stream_type=EventFilter.ALL, limit=1000):
        """
        Use this to get events for a given user. A chunk of event objects is returned for the user based on the
        parameters passed in.

        Args:
            - stream_position: where to start reading the events from.
              Can specify special case 'now', which is used to get the latest stream position and will return 0 events.
            - stream_type: a value from ``EventFilter`` that limits the type of events returned
            - limit: Limits the number of events returned.

        Returns:
            - a dictionary containing metadata & the events
        """

        query = {
            'stream_position': str(stream_position),
            'stream_type': stream_type,
            'limit': limit
        }

        response = self._get('events', query)
        self._handle_error(response)

        return response.json()

    def long_poll_for_events(self, stream_position=None, stream_type=EventFilter.ALL):
        """
        Blocks until new events are available
        Args:
            - stream_position: where to start reading the events from.
              Can specify special case 'now', which is used to get the latest stream position and will return 0 events.
            - stream_type: a value from ``EventFilter`` that limits the type of events returned

        """

        if not stream_position or stream_position == 'now':
            cursor = self.get_events(stream_position='now', stream_type=EventFilter.CHANGES)
            stream_position = cursor['next_stream_position']

        while True:
            poll_data = self._get_long_poll_data()
            url, query = poll_data['url'].split('?', 1)
            query = urlparse.parse_qs(query)

            query['stream_position'] = stream_position
            query['stream_type'] = stream_type
            response = requests.get(url, params=query)
            self._handle_error(response)

            poll_result = response.json()['message']
            if poll_result in ['new_message', 'new_change']:
                return stream_position

    def _get_long_poll_data(self):
        """
        Returns the information about the endpoint that will handle the actual long poll request.
        See http://developers.box.com/using-long-polling-to-monitor-events/ for details.
        """

        response = requests.options('https://api.box.com/2.0/events', headers=self._headers)
        self._handle_error(response)

        poll_data = response.json()['entries'][0]
        return poll_data

    @staticmethod
    def get_path_of_file(file_metadata):
        """
        returns the full path of a file.

        Args:
            - file_metadata: the dictionary as returned by the various Box apis.

        Returns:
            - The full path to the file
        """

        # skip over first part, which is 'All Files'
        path_parts = [x['name'].strip('/') for x in file_metadata['path_collection']['entries'][1:]]
        directory = '/' + '/'.join(path_parts)

        return path.join(directory, file_metadata['name'])


class BoxClientException(Exception):
    def __init__(self, message=None, status_code=None, object_id=None):
        super(BoxClientException, self).__init__(message)
        self.message = message
        self.status_code = status_code
        self.object_id = object_id


class ItemAlreadyExists(BoxClientException):
    pass


class ItemDoesNotExist(BoxClientException):
    pass


class PreconditionFailed(BoxClientException):
    pass


class BoxAuthenticationException(BoxClientException):
    pass


class BoxAccountUnauthorized(BoxClientException):
    pass
