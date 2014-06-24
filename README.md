⚠⚠⚠ WARNING WARNING WARNING ⚠⚠⚠
--------------------------------
This library is not under active development.
After spending 3 months trying to get support from Box, I finally gave up.

If anyone is interested in taking over development, please contact me [on Twitter](https://twitter.com/eiopa).



box.py - Python client for Box
------------------------------

[![Build Status](https://secure.travis-ci.org/sookasa/box.py.png?branch=master)](http://travis-ci.org/sookasa/box.py) [![Coverage Status](https://coveralls.io/repos/sookasa/box.py/badge.png)](https://coveralls.io/r/sookasa/box.py)


Usage example:
```python
from box import BoxClient
from StringIO import StringIO

client = BoxClient('user_token')
client.upload_file('hello.txt', StringIO('hello world'))
```


Supported features
----------------------------
- File download, upload and overwrite.
- Delete (including permanent delete), copy, move & restore
- Directory enumeration
- Link share
- User info fetch
- Thumbnails
- Search
- Events + longpoll
- Collaborations

Support
-------
- Python 2.6+
- PyPy (dependent on lxml at this point for the v1 authentication flow; see https://bitbucket.org/pypy/compatibility/wiki/lxml)

Installation
-------------
```
$ pip install box.py
```

Usage
=====

Uploading a file
----------------
```python
metadata = client.upload_file('hello.txt', StringIO('hello world'))
>>> metadata['id']
'123456'
```

Downloading a file
------------------
```python
response = client.download_file('123456')
>>> response.text
'hello world'
```

Deleting a file
---------------
```python
client.delete_file('123456')
```


Copying a file
--------------
```python
metadata = client.copy_file('123456', new_filename='goodbye.txt')
>>> metadata['id']
'654321'
```


Copying a folder
--------------
```python
metadata = client.copy_folder('361015', destination_parent='510163', new_foldername='goodbye')
>>> metadata['id']
'149148'
```


Receiving & waiting for events
------------------------------
```python
position = client.long_poll_for_events() # this will block until there are new events
events = client.get_events(position)
```

Authenticating a user
--------------------------
```python
from box import start_authenticate_v2, finish_authenticate_v2
url = start_authenticate_v2('my_api_key')
>>> url
'https://www.box.com/api/oauth2/authorize?response_type=code&client_id=my_api_key'
```

Next, redirect the user to url.
Once he accepts, a redirect will be issued to the page defined in your developer settings. The "code" is passed as a GET argument.

```python
http_get_params = ... # for django, this would be request.GET
response = finish_authenticate_v2('my_client_id', 'my_client_secret', http_get_params['code'])
>>> response
{ 'access_token': '1111111111111111',
  'restricted_to': [],
  'token_type': 'bearer',
  'expires_in': 4056,
  'refresh_token': '999998988888877766665555444433332221111'
}


client = BoxClient(response['access_token'])
```

### Token refresh
The v2 security API introduces a mandatory token refresh mechanism (according to Box, this was done to mitigate the impact of token theft).
Essentially, every so often, the token needs to be "refreshed", which involves hitting a Box endpoint with a special "refresh token", which returns new access  & refresh tokens that replace the old ones.
For more details, see here: http://developers.box.com/oauth/


The refresh dance can be performed explicitly as following:
```python
from box import refresh_v2_token
response = refresh_v2_token('my_client_id', 'my_client_secret', 'my_refresh_token')
>>> response
{ 'access_token': '2222222222222222',
  'restricted_to': [],
  'token_type': 'bearer',
  'expires_in': 4056,
  'refresh_token': '7777777777777777'
}
```

This can also be done automatically by the client, and you can register a callback that will notify you about the new tokens:
```python
def token_refreshed_callback(access_token, refresh_token):
	"""
	this gets called whenever the tokens have been refreshed. Should persist those somewhere.
	"""
	print 'new access token: ' + access_token
	print 'new refresh token: ' + refresh_token


from box import CredentialsV2
credentials = CredentialsV2('my_access_token', 'my_refresh_token', 'my_client_id', 'my_client_secret', refresh_callback=token_refreshed_callback)
client = BoxClient(credentials)

client.download_file(....) # if the tokens have expired, they will be refreshed automatically and token_refreshed_callback would get invoked
