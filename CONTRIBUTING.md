# How to contribute to nic-api

Firstly thank you for considering contributing to the project!

## Support questions

As the project is not very popular, you are free to use GitHub issues for
asking any related questions.

## Reporting issues

Include the following information in your post:

* Describe what you expected to happen;
* If possible, give info about your tariff in NIC.RU;
* If you are getting a parsing error, please include a raw XML response;
* Describe what actually happened; include the full traceback if there was an
 exception;
* List your Python, `nic-api`, `requests` and `requests-oauthlib` versions.

## Submitting patches

If there is not an open issue for what you want to submit, prefer opening one
for discussion before working on a PR. You can work on any issue that doesn't
have an open PR linked to it or a maintainer assigned to it. These show up in
the sidebar. No need to ask if you can work on an issue that interests you.

Include the following in your patch:

* Use [black](https://black.readthedocs.io) to format your code;
* If the issue does not require accessing the API, include tests;
* Update any relevant docs pages and docstrings. Docs pages and docstrings
 should be wrapped at 80 characters.
