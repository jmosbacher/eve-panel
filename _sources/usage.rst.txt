=====
Usage
=====

To use Eve-Panel in a project::

    import eve
    import eve_panel
    app = eve.Eve()
    client = eve_panel.EveClient.from_app(app)
    client.db.resource1.next_page()
