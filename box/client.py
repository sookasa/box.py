"""
A client library for working with Box's v2 API.
For extended specs, see: http://developers.box.com/docs/
"""
from datetime import datetime

from httplib import NOT_FOUND, PRECONDITION_FAILED, CONFLICT, UNAUTHORIZED
import json
import time
from urllib import urlencode
import urlparse

import requests


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


class CollaboratorRole(object):
    EDITOR = 'editor'
    VIEWER = 'viewer'
    PREVIEWER = 'previewer'
    UPLOADER = 'uploader'
    PREVIEWER_UPLOADER = 'previewer-uploader'
    VIEWER_UPLOADER = 'viewer-uploader'
    CO_OWNER = 'co-owner'


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

    user_dict = {}

    for x in content.user.iterchildren():
        user_dict[x.tag] = x.pyval

    return {
        'token': content.auth_token.text,
        'user': user_dict
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
        args['redirect_uri'] = redirect_uri

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

    return _handle_auth_response(response)


def _handle_auth_response(response):
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
        return {'Authorization': 'BoxAuth api_key={0}&auth_token={1}'.format(self._api_key, self._access_token)}

    def refresh(self):
        """
        V1 credentials cannot be refreshed, but doesn't expire either

        Always returns False
        """
        return False


class CredentialsV2(object):
    """
    v2 credentials
    Args:
        - access_token: The user access token
        - refresh_token: The user refresh token (optional)
        - client_id: The client_id you obtained in the initial setup (optional)
        - client_secret: The client_secret you obtained in the initial setup (optional)
        - refresh_call: A method that will be called when the tokens have been refreshed. Should take two arguments, access_token and refresh_token. (optional)
    """
    def __init__(self, access_token, refresh_token=None, client_id=None, client_secret=None, refresh_callback=None):
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_callback = refresh_callback

    @property
    def headers(self):
        return {'Authorization': 'Bearer {0}'.format(self._access_token)}

    def refresh(self):
        """
        Refreshes the access token based on the the refresh token, client id and secret if available.

        Returns True if the refresh was successful, False if the refresh could not be performed,
        and raises BoxAuthenticationException if the refresh failed
        """
        if not self._refresh_token or not self._client_id or not self._client_secret:
            return False

        result = refresh_v2_token(self._client_id, self._client_secret, self._refresh_token)

        self._access_token = result["access_token"]
        if "refresh_token" in result:
            self._refresh_token = result["refresh_token"]
        if self._refresh_callback:
            self._refresh_callback(self._access_token, self._refresh_token)

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

    def _check_for_errors(self, response):
        if not response.ok:
            exception = EXCEPTION_MAP.get(response.status_code, BoxClientException)
            raise exception(response.status_code, response.text)

    @property
    def default_headers(self):
        return self.credentials.headers

    def _request(self, method, resource, params=None, data=None, headers=None, endpoint="api", try_refresh=True, **kwargs):
        """
        Performs a HTTP request to Box.

        This method adds authentication headers, and performs error checking on the response.
        It also automatically tries to refresh tokens, if possible.
        Args:
            - method: The type of HTTP method, f.ex. get or post
            - resource: The resource to request (without shared prefix)
            - params: Any query parameters to send
            - data: Any data to send. If data is a dict, it will be encoded as json.
            - headers: Any additional headers
            - endpoint: The endpoint to use, f.ex. api or upload, defaults to api
            - try_refresh: True if a refresh of the credentials should be attempted, False otherwise
            - **kwargs: Any addiitonal arguments to pass to the request
        """

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

        self._check_for_errors(response)

        return response

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
        return self._request("get", 'users/' + username).json()

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

        return self._request("get", 'users/', params).json()

    def get_folder(self, folder_id=0, limit=100, offset=0, fields=None):
        """
        Retrieves the metadata of a folder and child directory/files.

        Args:
            - folder_id: the id of the folder you wish to query. No you can use paths :(
            - limit: (optional) number of items to return. (default=100, max=1000).
            - offset: (optional) The record at which to start
            - fields: (optional) Attribute(s) to include in the response
        """

        params = {
            'limit': limit,
            'offset': offset,
        }

        if fields:
            params['fields'] = ','.join(fields)

        return self._request("get", 'folders/{0}'.format(folder_id), params=params).json()

    def get_folder_content(self, folder_id=0, limit=100, offset=0, fields=None):
        """
        Retrieves the files and/or folders contained within this folder without any other metadata about the folder.

        Args:
            - folder_id: the id of the folder you wish to query. No you can use paths :(
            - limit: (optional) number of items to return. (default=100, max=1000).
            - offset: (optional) The record at which to start
            - fields: (optional) Attribute(s) to include in the response
        """

        params = {
            'limit': limit,
            'offset': offset,
        }

        if fields:
            params['fields'] = ','.join(fields)

        return self._request("get", 'folders/{0}/items'.format(folder_id), params=params).json()

    def get_folder_iterator(self, folder_id):
        """
        returns an iterator over the folder entries.
        this is equivalent of iterating over the folder pages manually
        """

        batch_size = 1000
        content = self.get_folder_content(folder_id, limit=batch_size)
        offset = 0
        while content['entries']:  # while the current batch has entries
            for entry in content['entries']:
                yield entry
            
            # stop if 'total_count' of entries (or more) has been fetched so far
            if  offset + len(content['entries']) >= content['total_count']:
                break
                
            # otherwise, fetch the next batch and repeat
            offset += batch_size
            content = self.get_folder_content(folder_id, limit=batch_size, offset=offset)

    def copy_folder(self, folder_id, destination_parent, new_foldername=None):
        """
        Copies a given `folder_id` into a new location, `destination_parent`. By default
        the original name of the folder is used unless `new_foldername` is provided.

        @see https://developers.box.com/docs/#folders-copy-a-folder

        Args:
            - file_id: the id of the file we want to copy
            - destination_parent: ID or a dictionary (as returned by the apis) of the target folder
            - new_foldername: (optional) name the copy `new_foldername`, if provided.

        Returns:
            - a dictionary containing the metadata of newly created copy
        """

        data = {
            'parent': {
            'id': self._get_id(destination_parent)
            }
        }

        if new_foldername:
            data.update({'name': new_foldername})

        return self._request('post', 'folders/{0}/copy'.format(folder_id), data=data).json()

    def create_folder(self, name, parent=0):
        """
        creates a new folder under the parent.

        Args:
            - parent: (optional) ID or a Dictionary (as returned by the apis) of the parent folder
        """
        data = {"name": name,
                'parent': {'id': self._get_id(parent)}}

        return self._request("post", 'folders', data=data).json()

    def get_folder_collaborations(self, folder_id):
        """
        Fetches the collaborations of the given folder_id

        Args:
            - folder_id: the folder id.

        Returns a list with all folder collaborations.
        """
        return self._request("get", 'folders/{0}/collaborations'.format(folder_id)).json()

    def get_file_metadata(self, file_id):
        """
        Fetches the metadata of the given file_id

        Args:
            - file_id: the file id.

        Returns a dictionary with all of the file metadata.
        """
        return self._request("get", 'files/{0}'.format(file_id)).json()

    def get_file_comments(self, file_id):
        """ Retrieves a file's associated comments

        Args:
            - file_id: the file id
        Returns a list of mini formatted comments
        """
        return self._request('get', 'files/{0}/comments'.format(file_id)).json()

    def get_file_tasks(self, file_id):
        """ Retrieves a file's associated tasks

        Args:
            - file_id: the file id
        Returns a list of mini formatted tasks
        """
        return self._request('get', 'files/{0}/tasks'.format(file_id)).json()

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

        self._request("delete", 'files/{0}'.format(file_id), headers=headers)

    def delete_folder(self, folder_id, etag=None, recursive=False):
        """
        Discards a folder to the trash.

        Args:
            - etag: (optional) If specified, the folder will only be deleted if its etag matches the parameter
            - recursive: (optional) If False, the folder will not be deleted if it contains files.
        """

        headers = {}
        if etag:
            headers['If-Match'] = etag

        params = {}
        if recursive:
            params['recursive'] = 'true'

        self._request("delete", 'folders/{0}'.format(folder_id), headers=headers, params=params)

    def delete_trashed_file(self, file_id):
        """
        Permanently deletes an item that is in the trash.
        """
        self._request("delete", 'files/{0}/trash'.format(file_id))

    def download_file(self, file_id, version=None):
        """
        Downloads a file

        Args:
            - file_id: The ID of the file to download.
            - version: (optional) The ID specific version of this file to download.

        Returns:
            - Request's response object
        """

        params = {}
        if version:
            params['version'] = version

        return self._request("get", 'files/{0}/content'.format(file_id), params=params, stream=True)

    def get_thumbnail(self, file_id, extension="png", min_height=None, max_height=None, min_width=None, max_width=None, max_wait=0):
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

        params = {}
        if min_height is not None:
            params['min_height'] = min_height
        if max_height is not None:
            params['max_height'] = max_height
        if min_width is not None:
            params['min_width'] = min_width
        if max_width is not None:
            params['max_width'] = max_width

        response = self._request("get", 'files/{0}/thumbnail.{1}'.format(file_id, extension), params=params, stream=True)
        if response.status_code == 202:
            # Thumbnail not ready yet
            ready_in_seconds = int(response.headers["Retry-After"])
            if ready_in_seconds > max_wait:
                return None

            # Wait for the thumbnail to get ready
            time.sleep(ready_in_seconds)

            response = self._request("get", 'files/{0}/thumbnail.{1}'.format(file_id, extension), params=params, stream=True)
            self._check_for_errors(response)
            return response.raw
        elif response.status_code == 302:
            # No thumbnail available
            return None
        else:
            return response.raw

    def upload_file(self, filename, fileobj, parent=0, content_created_at=None, content_modified_at=None):
        """
        Uploads a file. If the file already exists, ItemAlreadyExists is raised.

        Args:
            - filename: the filename to be used. If the file already exists, an ItemAlreadyExists exception will be
                        raised.
            - fileobj: a fileobj-like object that contains the data to upload
            - parent: (optional) ID or a Dictionary (as returned by the apis) of the parent folder
            - content_created_at: (optional) a timestamp (datetime or a properly formatted string) of the time the
              content was created
            - content_modified_at: (optional) a timestamp (datetime or a properly formatted string) of the time the
              content was last modified
        """

        form = {"parent_id": self._get_id(parent)}

        if content_created_at:
            form['content_created_at'] = content_created_at.isoformat() if isinstance(content_created_at, datetime) else content_created_at

        if content_created_at:
            form['content_modified_at'] = content_modified_at.isoformat() if isinstance(content_modified_at, datetime) else content_modified_at

        # usually Box goes with data==json, but here they want headers (as per standard http form)
        response = requests.post('https://upload.box.com/api/2.0/files/content',
                                 form,
                                 headers=self.default_headers,
                                 files={filename: (filename, fileobj)})

        self._check_for_errors(response)
        return response.json()['entries'][0]

    def overwrite_file(self, file_id, fileobj, etag=None, content_modified_at=None):
        """
        Overwrites an existing file. The file_id must exist on the server.
        Args:
            - fileid: the id of an existing file.
            - fileobj: a fileobj-like object that contains the data to upload
            - etag: an etag the file has to match in order to be overwritten. If the etags mismatch, an PreconditionFailed is raised
            - content_modified_at: (optional) a timestamp (datetime or a properly formatted string) of the time the
              content was created
        """
        headers = dict(self.default_headers)
        form = {}

        if etag:
            headers['If-Match'] = etag

        if content_modified_at:
            form['content_modified_at'] = content_modified_at.isoformat() if isinstance(content_modified_at, datetime) else content_modified_at

        response = requests.post('https://upload.box.com/api/2.0/files/{0}/content'.format(file_id),
                                 form,
                                 headers=headers,
                                 files={'file': fileobj})

        self._check_for_errors(response)
        return response.json()['entries'][0]

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

        data = {'parent': {'id': self._get_id(destination_parent)}}
        if new_filename:
            data['name'] = new_filename

        return self._request("post", 'files/{0}/copy'.format(file_id), data=data).json()

    def share_link(self, file_id, access=ShareAccess.OPEN, expire_at=None, can_download=None, can_preview=None):
        """
        Creates a share link for the file_id
        Args:
            - file_id: the id of the file we want to share
            - access: one of the values of ShareAccess
            - expire_at: (optional) a datetime representing the time the link will expire. Timestamps are rounded off
              to the given day.
            - can_download: Whether this link allows downloads. Can only be used with Open and Company
            - can_preview: Whether this link allows previewing. Can only be used with Open and Company

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
        data = {
            'access': access
        }

        if can_download is not None or can_preview is not None:
            data['permissions'] = {}
            if can_download is not None:
                data['permissions']['can_download'] = can_download
            if can_preview is not None:
                data['permissions']['can_preview'] = can_preview

        if expire_at:
            data['unshared_at'] = expire_at.isoformat()

        result = self._request("put", 'files/{0}'.format(file_id), data={'shared_link': data}).json()
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

        params = {
            'stream_position': str(stream_position),
            'stream_type': stream_type,
            'limit': limit
        }

        return self._request("get", 'events', params).json()

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
            self._check_for_errors(response)
            result = response.json()

            if result['message'] in ['new_message', 'new_change']:
                return stream_position

    def _get_long_poll_data(self):
        """
        Returns the information about the endpoint that will handle the actual long poll request.
        See http://developers.box.com/using-long-polling-to-monitor-events/ for details.
        """

        result = self._request('options', "events").json()
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
        path_parts.append(file_metadata['name'])
        return '/' + '/'.join(path_parts)

    def get_comment_information(self, comment_id):
        """ Retrieves information about a comment

        Args:
            - comment_id: the comment id
        Returns a full comment object
        """
        return self._request('get', 'comments/{0}'.format(comment_id)).json()

    def add_comment(self, id, type, message):
        """ Add a comment to the given file or comment

        Args:
            - id: the id of the object to comment
            - type: the type of the object to comment, can be "file" or "comment"
            - message: the comment's message

        Returns the newly created comment full object
        """

        item = {"type": type, "id": id}

        data = {'item': item, 'message': message}
        return self._request('post', 'comments', data=data).json()

    def change_comment(self, comment_id, message):
        """ Change a comment's message

        Args:
            - comment_id: the comment's to change id
            - message: the new message

        Returns the modified comment full object
        """
        data = {'message': message}
        return self._request('put', 'comments/{0}'.format(comment_id), data=data).json()

    def delete_comment(self, comment_id):
        """ Delete a given comment from box

        Args:
            - comment_id: the comment id

        """
        self._request('delete', 'comments/{0}'.format(comment_id))

    def get_task_information(self, task_id):
        """ Retrieves information about a task

        Args:
            - task_id: the task id
        Returns a full task object
        """
        return self._request('get', 'tasks/{0}'.format(task_id)).json()

    def add_task(self, file_id, due_at, action='review', message=None):
        """ Add a task to the given file

        Args:
            - file_id: the file to add a task to
            - due_at: a datetime object containing the due date
            - (optional) message: the task's message
            - (optional) action: currently only support 'review'

        Returns the newly created task full object
        """

        item = {"type": "file", "id": file_id}
        data = {
            'item': item,
            'action': action,
            'due_at': str(due_at),
            'message': message,
        }
        return self._request('post', 'tasks', data=data).json()

    def change_task(self, task_id, due_at, action='review', message=None):
        """ Change a task

        Args:
            - task_id: the task's to change id
            - due_at: a datetime for the day the task is due
            - (optional) message: the new task's message
            - (optional) action: currently only support 'review'

        Returns the modified task full object
        """

        data = {
            'action': action,
            'due_at': str(due_at),
        }
        if message:
            data['message'] = message

        return self._request('put', 'tasks/{0}'.format(task_id), data=data).json()

    def delete_task(self, task_id):
        """ Delete a given task from box

        Args:
            - task_id: the comment id

        """
        self._request('delete', 'tasks/{0}'.format(task_id))

    def get_task_assignments(self, task_id):
        """ Retrieves assignments for a given task

        Args:
            - task_id: the task id

        Returns the list of the task assignments (mini formatted)
        """
        return self._request('get', 'tasks/{0}/assignments'.format(task_id)).json()

    def get_assignment(self, assignment_id):
        """ Retrieves a given assignment information

        Args
            - assignment_id: the assignment id

        Returns an assignment full object
        """

        return self._request('get', 'task_assignments/{0}'.format(assignment_id)).json()

    def assign_task(self, task_id, user_id=None, login=None):
        """ Assign the given task to a user

        Args:
            - task_id: the task id
            - id: (optional) the id of the user to assign the task to
            - login: (optional) the login of the user to assign the task to
            At least the id or login field is to be set to identify the user

        Returns a full task assignment object
        """
        task = {"id": task_id, "type": "task"}
        assign_to = dict()
        if user_id:
            assign_to['id'] = user_id
        if login:
            assign_to['login'] = login

        data = {'task': task, 'assign_to': assign_to}

        return self._request('post', 'task_assignments', data=data).json()

    def update_assignment(self, assignment_id, resolution_state, message=None):
        """ Update a task assignment state

        Args:
          - assignment_id: the assignment to update id
          - message: (optional) A message about the state change
          - resolution_state: can be "completed", "incomplete", "approved" or "rejected"

        Returns the modified task assignment object
        """

        data = {'resolution_state': resolution_state}

        if message:
            data['message'] = message

        return self._request('put', 'task_assignments/{0}'.format(assignment_id), data=data).json()

    def delete_assignment(self, assignment_id):
        """ Delete the given assignment

        Args
            - assignment_id: the assignment id
        """

        self._request('delete', 'task_assignments/{0}'.format(assignment_id))

    def search(self, query, limit=30, offset=0):
        """
        The search endpoint provides a simple way of finding items that are accessible in a given user's Box account.

        Args:
            - query: The string to search for; can be matched against item names, descriptions, text content of a file,
                     and other fields of the different item types.
            - limit: (optional) number of items to return. (default=30, max=200).
            - offset: (optional) The record at which to start
        """

        params = {
            'query': query,
            'limit': limit,
            'offset': offset,
        }

        return self._request("get", 'search', params).json()

    def get_collaboration(self, collaboration_id):
        """
        Fetches the collaboration of the given collaboration_id

        Args:
            - collaboration_id: the collaboration id.

        Returns a dictionary with all of the collaboration data.
        """
        return self._request("get", 'collaborations/{0}'.format(collaboration_id)).json()

    def create_collaboration_by_user_id(self, folder_id, user_id, role=CollaboratorRole.VIEWER, notify=False):
        """
        Create a collaboration of the given folder_id and user_id

        Args:
            - folder_id: the folder id.
            - user_id: the user id.
            - role: (optional) access level of this collaboration from ``CollaboratorRole``. (default=CollaboratorRole.VIEWER)
            - notify: (optional) determines if the user should receive email notification of the collaboration. ``CollaboratorRole``. (default=False)

        Returns a dictionary with all of the collaboration data.
        """
        params = {
            'notify': notify,
        }
        data = {
            'item': {'id': folder_id, 'type': 'folder'},
            'accessible_by': {'id': user_id, 'type': 'user'},
            'role': role,
        }
        return self._request('post', 'collaborations', params, data=data).json()

    def create_collaboration_by_login(self, folder_id, login, role=CollaboratorRole.VIEWER, notify=False):
        """
        Create a collaboration of the given folder_id and login (login does not need to be a Box user)

        Args:
            - folder_id: the folder id.
            - login: the user login (does not need to be a Box user).
            - role: (optional) access level of this collaboration from ``CollaboratorRole``. (default=CollaboratorRole.VIEWER)
            - notify: (optional) determines if the user should receive email notification of the collaboration. ``CollaboratorRole``. (default=False)

        Returns a dictionary with all of the collaboration data.
        """
        params = {
            'notify': notify,
        }
        data = {
            'item': {'id': folder_id, 'type': 'folder'},
            'accessible_by': {'login': login, 'type': 'user'},
            'role': role,
        }
        return self._request('post', 'collaborations', params, data=data).json()

    def edit_collaboration(self, collaboration_id, role=CollaboratorRole.VIEWER, etag=None):
        """
        Edit an existing collaboration.

        Args:
            - collaboration_id: collaboration id to be edited
            - role: (optional) access level of this collaboration from ``CollaboratorRole``. (default=CollaboratorRole.VIEWER)
            - etag: (optional) If specified, the file will only be deleted if
                    its etag matches the parameter
        """

        headers = {}
        if etag:
            headers['If-Match'] = etag

        data = {
            'role': role,
        }
        return self._request('put', 'collaborations/{0}'.format(collaboration_id), headers=headers, data=data).json()

    def delete_collaboration(self, collaboration_id, etag=None):
        """
        Deletes a collaboration.

        Args:
            - collaboration_id: collaboration id to be deleted
            - etag: (optional) If specified, the file will only be deleted if
                    its etag matches the parameter
        """

        headers = {}
        if etag:
            headers['If-Match'] = etag

        self._request("delete", 'collaborations/{0}'.format(collaboration_id), headers=headers)


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
