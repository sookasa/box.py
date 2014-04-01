.. :changelog:

Release History
---------------

1.3.0
+++++
- Added collaboration (thanks @samkuehn)
- Added file comments & assignments (thanks @tsanch3z)
- Added folder copying (thanks @emiller)
- Fixed fields (thanks @samkuehn)

1.2.8
+++++
- Fixed get_thumbnail()

1.2.7
+++++
- Python 2.6 support (thanks @aaylward)

1.2.6
+++++
- Fixed: upload_file did not respect filename if the fileobj had a name attribute
- Fixed: long_poll_for_events() crashed (first appeared at 1.2.5)

1.2.5
+++++
- Fixed issue with delete_file raising an exception after deletion.
- Added content_created_at/content_modified_at to upload_file()
- Fixed content_modified_at in overwrite_file()

1.2.4
+++++
- Changed download() to return a requests.models.Response object rather than a fileobj. This makes it more convenient to
  work with responses, and also fixes the issue with encoded responses (gzip'd).

1.2.3
+++++
- Fixed get_path_of_file under Windows
- Added delete_folder() (thanks @echelon)

1.2.2
+++++
- Fixed redirect_uri

1.2.1
+++++
- Fixed upload (regression)

1.2
+++
A ton of stuff, courtesy of @holm   
  
- auto-refreshing for tokens
- lots of bugfixes
- thumbnails
- search

1.1
+++
- Added v2 oauth and made it the default
