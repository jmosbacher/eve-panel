
# -*- coding: utf-8 -*-

# DO NOT EDIT THIS FILE!
# This file has been autogenerated by dephell <3
# https://github.com/dephell/dephell

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


import os.path

readme = ''
here = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(here, 'README.rst')
if os.path.exists(readme_path):
    with open(readme_path, 'rb') as stream:
        readme = stream.read().decode('utf8')


setup(
    long_description=readme,
    name='eve_panel',
    version='0.3.4',
    description='Top-level package for Eve-Panel.',
    python_requires='>=3.7',
    project_urls={"documentation": "https://eve-panel.readthedocs.io", "homepage": "https://jmosbacher.github.io/eve-panel"},
    author='Yossi Mosbacher',
    author_email='joe.mosbacher@gmail.com',
    license='MIT',
    classifiers=['Development Status :: 2 - Pre-Alpha', 'Intended Audience :: Developers', 'License :: OSI Approved :: MIT License', 'Natural Language :: English', 'Programming Language :: Python :: 3', 'Programming Language :: Python :: 3.7', 'Programming Language :: Python :: 3.8'],
    packages=['eve_panel'],
    package_dir={"": "."},
    package_data={},
    install_requires=['eve==1.*,>=1.1.3', 'httpx==0.*,>=0.16.1', 'pandas', 'panel'],
    extras_require={"dask": ["dask"], "dev": ["bumpversion", "coverage", "flake8", "invoke", "isort", "nbsphinx", "numpydoc", "pylint", "pytest", "sphinx", "sphinx-material", "tox", "yapf"], "full": ["dask", "hvplot"], "plotting": ["hvplot"]},
)