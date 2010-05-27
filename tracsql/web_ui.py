
# stdlib imports
import datetime
import re
import string
import time
from math import floor, log
from operator import itemgetter

# trac imports
import trac
from trac.core import *
from trac.mimeview import Mimeview
from trac.perm import IPermissionRequestor
from trac.util import get_reporter_id
from trac.util.datefmt import pretty_timedelta, to_datetime
from trac.util.html import html, Markup
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.web.chrome import add_ctxtnav, add_stylesheet, add_script


def fmt_timestamp(seconds):
    millis = int(seconds * 1000) % 1000
    localtime = time.localtime(seconds)
    text = []
    text.append(time.strftime('%m/%d/%y  %H:%M:%S', localtime))
    text.append('.%03d' % millis)
    return "".join(text)


class TracSqlPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider)

    # INavigationContributor methods

    def get_active_navigation_item(self, req):
        return 'sql'

    def get_navigation_items(self, req):
        if not req.perm.has_permission('TRAC_ADMIN'):
            return
        yield 'mainnav', 'sql', html.A('SQL', href=req.href.sql())

    # ITemplateProvider methods

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('sql', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    # IRequestHandler methods

    def match_request(self, req):
        import re
        match = re.match(r'/sql(?:(/.*))?', req.path_info)
        if match:
            path, = match.groups()
            req.args['path'] = path or '/'
            return True

    def process_request(self, req):
        req.perm.require('TRAC_ADMIN')

        data = {}

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        db_str = self.env.config.get('trac', 'database')
        db_type, db_path = db_str.split(':', 1)
        data['db_type'] = db_type
        data['db_path'] = db_path

        if db_type == 'mysql':
            cursor.execute('set SQL_SELECT_LIMIT=1000')
        else:
            pass

        query = req.args.get('query', '')
        action = req.args.get('action', '')

        if action == 'tables':
            if db_type == 'mysql':
                sql = 'show tables'
            elif db_type == 'sqlite':
                sql = 'SELECT name FROM sqlite_master WHERE type = "table"'
            else:
                assert False, "Unsupported db_type: %s" % db_type
        elif action == 'database':
            if db_type == 'mysql':
                sql = 'show databases'
            elif db_type == 'sqlite':
                sql = 'PRAGMA database_list'
            else:
                assert False, "Unsupported db_type: %s" % db_type
        else:
            sql = query

        format = {
            'rev' : lambda x: html.A(x, href=req.href.changeset(x)),
            'time' : lambda x: fmt_timestamp(x),
        }

        if trac.__version__.startswith('0.12'):
            format['time'] = lambda x: fmt_timestamp(x/1000000.)

        format['changetime'] = format['time']

        if action == 'tables':
            if db_type == 'mysql':
                describe = 'describe %s'
            elif db_type == 'sqlite':
                describe = 'PRAGMA table_info("%s")'
            else:
                assert False, "Unsupported db_type: %s" % db_type
            format['name'] = lambda x: html.A(x, href=req.href.sql(query=describe % x))

        default = lambda x: x

        error = None

        if sql.strip():
            try:
                cursor.execute(sql)
                cols = map(lambda x: x[0], cursor.description)
                rows = cursor.fetchall()[:1000]
            except BaseException, e:
                error = e.message
                cols = rows = []
        else:
            cols = rows = []

        # FIXME: Optionally format the row values? e.g., "raw" output?
        formats = [format.get(col, default) for col in cols]
        for i, row in enumerate(rows):
            rows[i] = [fmt(col) for fmt, col in zip(formats, row)]

        data['query'] = query
        data['error'] = error
        data['cols'] = cols
        data['rows'] = rows

        cursor.close()

        # Include trac wiki stylesheet
        add_stylesheet(req, 'common/css/wiki.css')

        # Include trac stats stylesheet
        add_stylesheet(req, 'sql/common.css')

        # Include javascript libraries
        add_script(req, 'stats/jquery-1.4.2.min.js')

        # Include context navigation links
        add_ctxtnav(req, 'Query', req.href.sql())
        # FIXME: add_ctxtnav(req, 'Schema', req.href.sql('schema'))

        return 'sql.html', data, None


