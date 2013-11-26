"""
A client library for working with Box's v2 API.
For extended specs, see: http://developers.box.com/docs/
"""

from httplib import NOT_FOUND, PRECONDITION_FAILED, CONFLICT, UNAUTHORIZED
import json
from urllib import urlencode
import urlparse
import requests
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


def start_authenticate_v1(api_key):
    """
    Returns a url to redirect the client to. Expires after 10 minutes.
    Note that according to Box, this endpoint will cease to function after December 31st.
    """
    from lxml import objectify

    r = requests.get('https://www.box.com/api/1.0/rest?action=get_ticket&api_key=%s' % api_key)
    if not r.ok:
        raise BoxAuthenticationException(r.status_code, r.text)

    content = objectify.fromstring(str(r.text))
    if content.status != 'get_ticket_ok':
        raise BoxAuthenticationException(r.status_code, content.status.text)

    return 'https://www.box.com/api/1.0/auth/%s' % content.ticket

def finish_authenticate_v1(api_key, ticket):
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
    from lxml import objectify
    r = requests.get('https://www.box.com/api/1.0/rest', params={'action': 'get_auth_token',
                                                                 'api_key': api_key,
                                                                 'ticket': ticket})
    if not r.ok:
        raise BoxAuthenticationException(r.status_code, r.text)

    content = objectify.fromstring(str(r.text))
    if content.status != 'get_auth_token_ok':
        raise BoxAuthenticationException(r.status_code, content.status.text)

    return {
        'token': content.auth_token.text,
        'user': {x.tag: x.pyval for x in content.user.iterchildren()}
    }

def start_authenticate_v2(client_id, state=None, redirect_uri=None):
    """
    Returns a url to redirect the client to.

    Args:
        - client_id: The client_id you obtained in the initial setup.
        - redirect_uri: An HTTPS URI or custom URL scheme where the response will be redirected.
                        Optional if the redirect URI is registered with Box already.
        - state: An arbitrary string of your choosing that will be included in the response to your application

    Returns:
        - a url to redirect to user to.
    """
    args = {
        'response_type': 'code',
        'client_id': client_id,
    }

    if state:
        args['state'] = state

    if redirect_uri:
        args['redirect_url'] = redirect_uri

    return 'https://www.box.com/api/oauth2/authorize?' + urlencode(args)

def finish_authenticate_v2(client_id, client_secret, code):
    """
    finishes the authentication flow. See http://developers.box.com/oauth/ for details.

    Args:
        - client_id: The client_id you obtained in the initial setup.
        - client_secret: The client_secret you obtained in the initial setup.
        - code: a string containing the code, or a dictionary containing the GET query

    Returns:
        - a dictionary with the token and additional info

    Example output:
    { 'access_token': 'T9cE5asGnuyYCCqIZFoWjFHvNbvVqHjl',
      'expires_in': 3600,
      'restricted_to': [],
      'token_type': 'bearer',
      'refresh_token': 'J7rxTiWOHMoSC1isKZKBZWizoRXjkQzig5C6jFgCVJ9bUnsUfGMinKBDLZWP9BgR',
    }

    """
    return _oauth2_token_request(client_id, client_secret, 'authorization_code', code=code)



def refresh_v2_token(client_id, client_secret, refresh_token):
    """
    Returns a new access_token & refresh_token from an existing refresh_token

    Each access_token is valid for 1 hour. In order to get a new, valid token, you can use the accompanying
    refresh_token. Each refresh token is valid for 14 days. Every time you get a new access_token by using a
    refresh_token, we reset your timer for the 14 day period. This means that as long as your users use your
    application once every 14 days, their login is valid forever.

    Args:
        - client_id: The client_id you obtained in the initial setup.
        - client_secret: The client_secret you obtained in the initial setup.
        - code: a string containing the code, or a dictionary containing the GET query

    Returns:
        - a dictionary with the token and additional info
    """
    return _oauth2_token_request(client_id, client_secret, 'refresh_token', refresh_token=refresh_token)

def _oauth2_token_request(client_id, client_secret, grant_type, **kwargs):
    """
    Performs an oauth2 request against Box
    """
    args = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': grant_type
    }

    args.update(kwargs)
    response = requests.post('https://www.box.com/api/oauth2/token', args)
    result = response.json()
    if 'error' in result:
        raise BoxAuthenticationException(response.status_code, message=result.get('error_description'), error=result['error'])
    return result

class CredentialsV1(object):
    """
    v1 credentials
    Args:
        - api_key: Your Box api_key
        - access_token: the user access token
    """
    def __init__(self, api_key, access_token):
        self._api_key = api_key
        self._access_token = access_token

    @property
    def headers(self):
        return {'Authorization': 'BoxAuth api_key={}&auth_token={}'.format(self._api_key, self._access_token)}

    def refresh(self):
        return False

class CredentialsV2(object):
    """
    v2 credentials
    Args:
        - access_token: the user access token
    """
    def __init__(self, access_token, refresh_token=None, client_id=None, client_secret=None, refresh_callback=None):
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_callback = refresh_callback

    @property
    def headers(self):
        return {'Authorization': 'Bearer {}'.format(self._access_token)}

    def refresh(self):
        if not self._refresh_token or not self._client_id or not self._client_secret:
            return False

        result = refresh_v2_token(self._client_id, self._client_secret, self._refresh_token)

        self._access_token = result["access_token"]
        if self._refresh_callback:
            self._refresh_callback(self._access_token)

        return True


class BoxClient(object):

    def __init__(self, credentials):
        """
        Args:
            - credentials: an access_token string, or an instance of CredentialsV1/CredentialsV2
        """
        if not hasattr(credentials, 'headers'):
            credentials = CredentialsV2(credentials)

        self.credentials = credentials

    def _process_response(self, response, raw=False):
        if not response.ok:
            exception = EXCEPTION_MAP.get(response.status_code, BoxClientException)
            raise exception(response.status_code, response.text)

        if response.status_code == 202:
            return response.headers["Location"]

        if raw:
            return response.raw
        else:
            return response.json()

    @property
    def default_headers(self):
        return self.credentials.headers

    def _request(self, method, resource, params=None, data=None, headers=None, try_refresh=True, endpoint="api", raw=False, **kwargs):
        if isinstance(data, dict):
            data = json.dumps(data)

        if headers:
            headers = dict(headers)
            headers.update(self.default_headers)
        else:
            headers = self.default_headers

        url = 'https://%s.box.com/2.0/%s' % (endpoint, resource)

        response = requests.request(method, url, params=params, data=data, headers=headers, **kwargs)

        if response.status_code == UNAUTHORIZED and try_refresh and self.credentials.refresh():
            return self._request(method, resource, params, data, headers, try_refresh=False, **kwargs)

        return self._process_response(response, raw=raw)

    def _get(self, resource, query=None, **kwargs):
        return self._request("get", resource, params=query, **kwargs)

    def _post(self, resource, data=None, **kwargs):
        return self._request("post", resource, data=data, **kwargs)

    def _put(self, resource, data=None, **kwargs):
        return self._request("put", resource, data=data, **kwargs)

    def _delete(self, resource, headers=None, **kwargs):
        return self._request("delete", resource, headers=headers, **kwargs)

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

    def get_user_info(self, username=None):
        """
        Returns info.

        Args:
            - username: The username to query. If None then the info on the current user will
                        be returned

        """
        username = username or 'me'
        return self._get('users/' + username)

    def get_user_list(self, limit=100, offset=0):
        """
        Returns users in an enterprise.

        Args:
            - limit: number of users to return. (default=100, max=1000). Optional.
            - offset: The record at which to start. Optional.
        """

        params = {
            'limit': limit,
            'offset': offset,
        }

        return self._get('users/', params)

    def get_folder(self, folder_id, limit=100, offset=0, fields=None):
        """
        Retrieves the metadata of a folder and child directory/files.

        Args:
            - limit: (optional) number of items to return. (default=100, max=1000).
            - offset: (optional) The record at which to start
            - fields: (optional) Attribute(s) to include in the response
        """

        params = {
            'limit': limit,
            'offset': offset,
        }

        if fields:
            params['fields'] = fields

        return self._get('folders/{}'.format(folder_id), params)

    def get_folder_content(self, folder_id, limit=100, offset=0, fields=None):
        """
        Retrieves the files and/or folders contained within this folder without any other metadata about the folder.

        Args:
            - limit: (optional) number of items to return. (default=100, max=1000).
            - offset: (optional) The record at which to start
            - fields: (optional) Attribute(s) to include in the response
        """

        params = {
            'limit': limit,
            'offset': offset,
        }

        if fields:
            params['fields'] = fields

        return self._get('folders/{}/items'.format(folder_id), params)

    def get_folder_iterator(self, folder_id):
        """
        returns an iterator over the folder entries.
        this is equivalent of iterating over the folder pages manually
        """

        batch_size = 1000
        content = self.get_folder_content(folder_id, limit=batch_size)
        offset = 0
        while content['entries']:
            for entry in content['entries']:
                yield entry

            offset += batch_size
            content = self.get_folder_content(folder_id, limit=batch_size, offset=offset)

    def create_folder(self, name, parent=0):
        """
        creates a new folder under the parent.

        Args:
            - parent: (optional) ID or a Dictionary (as returned by the apis) of the parent folder
        """
        args = {"name": name}
        args['parent'] = {'id': self._get_id(parent)}

        return self._post('folders', args)

    def get_file_metadata(self, file_id):
        """
        Fetches the metadata of the given file_id

        Args:
            - file_id: the file id.

        Returns a dictionary with all of the file metadata.
        """
        return self._get('files/{}'.format(file_id))

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

        self._delete('files/{}'.format(file_id), headers)

    def delete_trashed_file(self, file_id):
        """
        Permanently deletes an item that is in the trash.
        """
        self._delete('files/{}/trash'.format(file_id))

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

        return self._get('files/{}/content'.format(file_id), query=query, stream=True, raw=True)

    def get_thumbnail_url(self, file_id, extension="png", min_height=None, max_height=None, min_width=None, max_width=None):
        """
        Downloads a file

        Args:
            - file_id: The ID of the file to download.
            - extension:  Currently thumbnails are only available png
            - min_height: (optional) The minimum height of the thumbnail.
            - max_height: (optional) The maximum height of the thumbnail
            - min_width: (optional) The minimum width of the thumbnail
            - max_width: (optional) The maximum width of the thumbnail

        Returns a file-like object to the file content
        """

        query = {}
        if min_height:
            query['min_height'] = min_height
        if max_height:
            query['max_height'] = max_height
        if min_width:
            query['min_width'] = min_width
        if max_width:
            query['max_width'] = max_width

        return self._get('files/{}/thumbnail.{}'.format(file_id, extension), query=query)

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
        result = self._request("post", "files/content", endpoint="upload", data=form, files={filename: fileobj})
        return result['entries'][0]

    def overwrite_file(self, file_id, fileobj, etag=None, content_modified_at=None):
        """
        Uploads a file that will overwrite an existing one. The file_id must exist on the server.
        """
        headers = {}
        if etag:
            headers['If-Match'] = etag

        if content_modified_at:
            headers['content_modified_at'] = content_modified_at.isoformat()

        result = self._request("post", 'files/{}/content'.format(file_id), headers=headers, endpoint="upload", files={'file': fileobj})
        return result['entries'][0]

    def copy_file(self, file_id, destination_parent, new_filename=None):
        """
        Copies a file
        @see http://developers.box.com/docs/#files-copy-a-file

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

        return self._post('files/{}/copy'.format(file_id), args)

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

        result = self._put('files/{}'.format(file_id), {'shared_link': args})
        return result['shared_link']

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

        return self._get('events', query)

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
            result = self._process_response(response)

            if result['message'] in ['new_message', 'new_change']:
                return stream_position

    def _get_long_poll_data(self):
        """
        Returns the information about the endpoint that will handle the actual long poll request.
        See http://developers.box.com/using-long-polling-to-monitor-events/ for details.
        """

        result = self._request('options', "events")
        return result['entries'][0]

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

    def search(self, query, limit=30, offset=0):
        """
        The search endpoint provides a simple way of finding items that are accessible in a given user's Box account.

        Args:
            - query: The string to search for; can be matched against item names, descriptions, text content of a file, and other fields of the different item types.
            - limit: (optional) number of items to return. (default=30, max=200).
            - offset: (optional) The record at which to start
        """

        params = {
            'query': query,
            'limit': limit,
            'offset': offset,
        }

        return self._get('search', params)


class BoxClientException(Exception):
    def __init__(self, status_code, message=None, **kwargs):
        super(BoxClientException, self).__init__(message)
        self.status_code = status_code
        self.message = message
        self.__dict__.update(kwargs)


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


EXCEPTION_MAP = {
    CONFLICT: ItemAlreadyExists,
    NOT_FOUND: ItemDoesNotExist,
    PRECONDITION_FAILED: PreconditionFailed,
    UNAUTHORIZED: BoxAccountUnauthorized
}
