# TracSQL

The TracSQL project is a plugin for the Trac project management tool.

A "SQL" tab is added to the Trac project.  Inside this tab, the plugin
supports interacting with the project database.

Some features include:

* perform queries on the project database
* view results as raw or formatted (and hyper-linked) output
* export result set in CSV
* browse the database schema (including table and index information)

This plugin supports Trac installations with **SQLite**, **MySQL**, and
**PostgreSQL** database backends (although the queries will need to be
written differently according to which SQL database is being used).


# Installation

The TracSQL plugin can be installed using standard:

    $ easy_install tracsql

Or, grab the sources and build using:

    $ python setup.py install


# Configuration

It is configured in the ``trac.ini`` file by enabling and configuring:

    [components]
    tracsql.* = enabled

The ``TRAC_ADMIN`` permission is used to control access to the query pages.

By default, the TracSQL plugin connects to the project database.  To use an
external database, set the ``database`` parameter in the ``tracsql`` section
of the ``trac.ini`` file to a valid database connection string:

    [tracsql]
    database = sqlite:db/external.db


# Examples

Some screensots, showing a few of the features:

![SQL Query](tracsql/raw/master/docs/sql-query.png)

![SQL Schema](tracsql/raw/master/docs/sql-schema.png)
