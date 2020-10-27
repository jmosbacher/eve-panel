# -*- coding: utf-8 -*-

# DO NOT EDIT THIS FILE!
# This file has been autogenerated by dephell <3
# https://github.com/dephell/dephell

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

readme = ''

setup(
    long_description=readme,
    name='eve_panel',
    version='0.1.0',
    description='Top-level package for Eve-Panel.',
    python_requires='>=3.7',
    author='Yossi Mosbacher',
    author_email='joe.mosbacher@gmail.com',
    packages=['eve_panel'],
    package_dir={"": "."},
    package_data={},
    install_requires=[
        'bokeh==2.2.3; python_version >= "3.6"',
        'cerberus==1.3.2; python_version >= "2.7"', 'certifi==2020.6.20',
        'click==7.1.2; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version != "3.4.*" and python_version >= "2.7"',
        'eve==1.1.4; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version != "3.4.*" and python_version >= "2.7"',
        'events==0.3',
        'flask==1.1.2; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version != "3.4.*" and python_version >= "2.7"',
        'h11==0.11.0', 'httpcore==0.12.0; python_version >= "3.6"',
        'httpx==0.16.1; python_version >= "3.6"',
        'idna==2.10; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version >= "2.7"',
        'importlib-metadata==2.0.0; python_version < "3.8" and python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version != "3.4.*" and python_version >= "2.7"',
        'itsdangerous==1.1.0; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version >= "2.7"',
        'jinja2==2.11.2; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version != "3.4.*" and python_version >= "2.7"',
        'markdown==3.3.3; python_version >= "3.6"',
        'markupsafe==1.1.1; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version >= "2.7"',
        'nested-dict==1.61', 'numpy==1.19.2; python_version >= "3.6"',
        'packaging==20.4; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version >= "2.7"',
        'pandas==1.1.3; python_version >= "3.6.1"',
        'panel==0.9.7; python_version >= "3.6"',
        'param==1.10.0; python_version >= "2.7"',
        'pillow==8.0.1; python_version >= "3.6"',
        'pyct==0.4.8; python_version >= "2.7"',
        'pymongo==3.11.0; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version >= "2.7"',
        'pyparsing==2.4.7; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version >= "2.6"',
        'python-dateutil==2.8.1; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version >= "2.7"',
        'pytz==2020.1', 'pyviz-comms==0.7.6',
        'pyyaml==5.3.1; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version != "3.4.*" and python_version >= "2.7"',
        'rfc3986==1.4.0',
        'simplejson==3.17.2; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version >= "2.5"',
        'six==1.15.0; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version >= "2.7"',
        'sniffio==1.2.0; python_version >= "3.5"',
        'tornado==6.0.4; python_version >= "3.5"',
        'tqdm==4.51.0; python_version != "3.0.*" and python_version != "3.1.*" and python_version >= "2.6"',
        'typing-extensions==3.7.4.3',
        'werkzeug==1.0.1; python_version != "3.0.*" and python_version != "3.1.*" and python_version != "3.2.*" and python_version != "3.3.*" and python_version != "3.4.*" and python_version >= "2.7"',
        'zipp==3.4.0; python_version < "3.8" and python_version >= "3.6"'
    ],
    extras_require={
        "dev": [
            "alabaster==0.7.12", "appdirs==1.4.4",
            "astroid==2.4.2; python_version >= \"3.5\"",
            "atomicwrites==1.4.0; sys_platform == \"win32\" and python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "attrs==20.2.0; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "babel==2.8.0; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "bump2version==1.0.1; python_version >= \"3.5\"",
            "bumpversion==0.6.0", "chardet==3.0.4",
            "colorama==0.4.4; (sys_platform == \"win32\" or platform_system == \"Windows\") and python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version != \"3.4.*\" and python_version >= \"2.7\"",
            "coverage==4.4.2", "distlib==0.3.1",
            "docutils==0.16; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version != \"3.4.*\" and python_version >= \"2.7\"",
            "filelock==3.0.12",
            "flake8==3.8.4; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "imagesize==1.2.0; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "iniconfig==1.1.1", "invoke==1.4.1",
            "isort==4.3.21; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "lazy-object-proxy==1.4.3; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "mccabe==0.6.1",
            "pluggy==0.13.1; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "py==1.9.0; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "pycodestyle==2.6.0; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "pyflakes==2.2.0; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "pygments==2.7.2; python_version >= \"3.5\"",
            "pylint==2.6.0; python_version >= \"3.5.0\"",
            "pytest==6.1.1; python_version >= \"3.5\"",
            "requests==2.24.0; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version != \"3.4.*\" and python_version >= \"2.7\"",
            "snowballstemmer==2.0.0",
            "sphinx==3.2.1; python_version >= \"3.5\"",
            "sphinxcontrib-applehelp==1.0.2; python_version >= \"3.5\"",
            "sphinxcontrib-devhelp==1.0.2; python_version >= \"3.5\"",
            "sphinxcontrib-htmlhelp==1.0.3; python_version >= \"3.5\"",
            "sphinxcontrib-jsmath==1.0.1; python_version >= \"3.5\"",
            "sphinxcontrib-qthelp==1.0.3; python_version >= \"3.5\"",
            "sphinxcontrib-serializinghtml==1.1.4; python_version >= \"3.5\"",
            "toml==0.10.1",
            "tox==3.20.1; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version != \"3.4.*\" and python_version >= \"2.7\"",
            "typed-ast==1.4.1; implementation_name == \"cpython\" and python_version < \"3.8\"",
            "urllib3==1.22",
            "virtualenv==20.1.0; python_version != \"3.0.*\" and python_version != \"3.1.*\" and python_version != \"3.2.*\" and python_version != \"3.3.*\" and python_version >= \"2.7\"",
            "wrapt==1.12.1", "yapf==0.30.0"
        ]
    },
)
