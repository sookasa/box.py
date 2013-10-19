box.py - Python client for Box
------------------------------

[![Build Status](https://secure.travis-ci.org/sookasa/box.py.png?branch=master)](http://travis-ci.org/sookasa/box.py) [![Coverage Status](https://coveralls.io/repos/sookasa/box.py/badge.png)](https://coveralls.io/r/sookasa/box.py)


Usage example:
```python
from box import BoxClient
from StringIO import StringIO

client = BoxClient('my_api_key', 'user_token')
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
- Python 2.7 (other versions not yet verified)


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
---------------------
```python
from box import get_auth_url_v1, box_authentication_done
url = get_auth_url_v1('my_api_key')

# redirect the user to url.
# Once he accepts, a redirect will be issued to the page defined in your developer settings.
# The "ticket" is passed as a GET argument
response = finish_authenticate('my_api_key', request.REQUEST['ticket'])
>>> response
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
```
