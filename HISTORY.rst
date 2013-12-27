.. :changelog:

Release History
---------------

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
