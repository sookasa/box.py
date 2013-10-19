box.py - a Python client for Box's v2 api
-----------------------------------------

[![Build Status](https://secure.travis-ci.org/sookasa/box.py.png?branch=master)](http://travis-ci.org/sookasa/box.py)


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
----------------
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


Receving & waiting for events
------------------
```python
position = client.long_poll_for_events() # this will block until there are new events
events = client.get_events(position)
```