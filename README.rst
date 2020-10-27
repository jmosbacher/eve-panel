=========
Eve-Panel
=========


.. image:: https://img.shields.io/pypi/v/eve_panel.svg
        :target: https://pypi.python.org/pypi/eve_panel

.. image:: https://img.shields.io/travis/jmosbacher/eve_panel.svg
        :target: https://travis-ci.com/jmosbacher/eve_panel

.. image:: https://readthedocs.org/projects/eve-panel/badge/?version=latest
        :target: https://eve-panel.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status



Dynamically create an httpx based client for any Eve api that uses Param for type enforcement and Panel for GUIs.
This is just a prototype package,features will slowly be added as i need them for my own purposes.
The api is expected to change without warning based on my needs but feel free to fork or copy parts and adapt to your own needs.

To view the widgets in a notebook you will need to install the pyviz plugin. For details, see panel docs.
.. code-block:: python

        import eve
        from eve_panel import EveApiClient, EveDomain

        app = eve.Eve()

        client = eve_panel.EveApiClient.from_app_config(app.config, address="http://localhost:5000")
        client.auth.token = "my-secret-token"

        api = eve_panel.EveDomain.from_domain_def("my_api_name", app.config["DOMAIN"], client=client)

        # show a resources gui
        api.resource_name 

        # get a specific item
        api.resource_name["item_id"]

        # get current page data
        api.resource_name.current_page()

        # get next page data
        api.resource_name.next_page()

        # get previous page data
        api.resource_name.previous_page()


* Free software: MIT
* Documentation: https://eve-panel.readthedocs.io.


Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `briggySmalls/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`briggySmalls/cookiecutter-pypackage`: https://github.com/briggySmalls/cookiecutter-pypackage
