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



Dynamically create an httpx based client for any Eve api. Uses Param + Cerberus for type enforcement and Panel for GUIs.
This is just a prototype package,features will slowly be added as i need them for my own purposes.
The api is expected to change without warning based on my needs but feel free to fork or copy parts and adapt to your own needs.

To view the widgets in a notebook you will need to install the pyviz plugin. For details, see panel docs.

Usage
-----

.. code-block:: python

    import eve
    from eve_panel import EveClient


    app = eve.Eve()

    api = eve_panel.EveClient.from_app(app)
    
    # optional
    api.set_token("my-secret-token")

    # show a resources gui
    api.resource_name

    # get a specific item
    api.resource_name["item_id"]

    # get current page
    api.resource_name.current_page()

    # get next page
    api.resource_name.next_page()

    # get previous page
    api.resource_name.previous_page()

    # insert new documents
    docs = [{"name": "new document"}]
    api.resource_name.insert_documents(docs)
    


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
