# TracSQL

The TracSQL project is a plugin for the [trac](https://trac.edgewall.org/)
project management tool.

A "SQL" tab is added to the Trac project.  Inside this tab, the plugin
supports interacting with the project database.

Some features include:

* Perform queries on the project database
* View results as raw or formatted (and hyper-linked) output
* Export result set in CSV
* Browse the database schema (including table and index information)

This plugin supports Trac installations with **SQLite**, **MySQL**, and
**PostgreSQL** database backends (although your raw queries may need to be
written differently according to which SQL database is being used).


## Installation

The TracSQL plugin can be installed using standard:

```
$ pip install tracsql
```

Or, grab the sources and build using:

```
$ python setup.py install
```

## Configuration

It is configured in the ``trac.ini`` file by enabling and configuring:

```ini
[components]
tracsql.* = enabled
```

The ``TRAC_ADMIN`` permission is used to control access to the query pages.

By default, the TracSQL plugin connects to the project database.  To use an
external database, set the ``database`` parameter in the ``tracsql`` section
of the ``trac.ini`` file to a valid database connection string:

```ini
[tracsql]
database = sqlite:db/external.db
```

# Examples

Some screensots, showing a few of the features:

![SQL Query](https://github.com/trac-hacks/tracsql/raw/master/docs/sql-query.png)

![SQL Schema](https://github.com/trac-hacks/tracsql/raw/master/docs/sql-schema.png)
