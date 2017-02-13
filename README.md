Value Caching Service
=====================

A service to query remote URL with params to get a corresponding hash value.
 
Usage
-----
`python caching_service.py`
In another terminal the service can be queried like this: `curl localhost:8000/from_cache?key=123`

TODOs
-----

* Review response codes
* Use logger instead of prints
* Implement a separate API for users
