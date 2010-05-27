#!/usr/bin/env python

from setuptools import setup, find_packages

PACKAGE = 'TracSQL'
VERSION = '0.1'

setup(
    name=PACKAGE, version=VERSION,
    description="A plugin for querying the project database",
    packages=find_packages(exclude=['ez_setup', '*.tests*']),
    package_data={
        'tracsql': [
            'htdocs/*.css',
            'htdocs/*.png',
            'htdocs/*.gif',
            'htdocs/*.js',
            'templates/*.html'
        ]
    },
    entry_points = {
        'trac.plugins': [
            'tracsql.web_ui = tracsql.web_ui',
        ]
    }
)

