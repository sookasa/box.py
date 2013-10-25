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


Currently supported features
----------------------------
- File download, upload and overwrite.
- Delete (including permanent delete), copy, move & restore
- Directory enumeration
- Link share
- User info fetch
- Events + longpoll


Support
-------
- Python 2.7
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
data = client.download_file('123456')
>>> data.read()
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
response = finish_authenticate_v2('my_client_id', 'my_client_secret', request.REQUEST['code'])
>>> response
{ 'access_token': '1111111111111111',
  'restricted_to': [],
  'token_type': 'bearer',
  'expires_in': 4056,
  'refresh_token': '999998988888877766665555444433332221111'
}


client = BoxClient(response['access_token'])
```

You will need to refresh the token (according to the "expires_in" field) on occassion:
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

