
# stdlib imports
import re
import time

# trac imports
import trac
from trac.core import *
from trac.util.html import html
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

        path = req.args.get('path', '')

        data = {}

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        db_str = self.env.config.get('trac', 'database')
        db_type, db_path = db_str.split(':', 1)
        assert db_type in ('sqlite', 'mysql', 'postgres'), \
                            'Unsupported database "%s"' % db_type
        self.db_type = db_type

        # Include trac wiki stylesheet
        add_stylesheet(req, 'common/css/wiki.css')

        # Include trac stats stylesheet
        add_stylesheet(req, 'sql/common.css')

        # Include javascript libraries
        add_script(req, 'stats/jquery-1.4.2.min.js')

        # Include context navigation links
        add_ctxtnav(req, 'Query', req.href.sql())
        add_ctxtnav(req, 'Schema', req.href.sql('schema'))

        if path == '/':
            result = self._process(req, cursor, data)
            cursor.close()
            return result

        elif path == '/schema':
            result = self._process_schema(req, cursor, data)
            cursor.close()
            return result

        else:
            cursor.close()
            raise ValueError, "unknown path '%s'" % path

    def _process(self, req, cursor, data):

        if self.db_type == 'mysql':
            cursor.execute('set SQL_SELECT_LIMIT=1000')
        else:
            pass

        sql = req.args.get('query', '')
        raw = req.args.get('raw', '')

        cols = rows = []
        took = 0
        error = None

        if re.search('.*delete|drop|insert|replace|set|update.*', sql,
                     re.IGNORECASE):
            error = "Query must be read-only!"

        elif sql.strip():
            try:
                start = time.time()
                cursor.execute(sql)
                cols = map(lambda x: x[0], cursor.description)
                rows = cursor.fetchall()[:1000]
                took = '%.3f' % (time.time() - start)
            except BaseException, e:
                error = e.message

        if not raw:

            format = {
                'path' : lambda x: html.A(x, href=req.href.browser(x)),
                'rev' : lambda x: html.A(x, href=req.href.changeset(x)),
                'time' : lambda x: fmt_timestamp(x),
            }

            if trac.__version__.startswith('0.12'):
                format['time'] = lambda x: fmt_timestamp(x/1000000.)

            format['base_path'] = format['path']
            format['base_rev'] = format['rev']
            format['changetime'] = format['time']

            default = lambda x: x

            formats = [format.get(col, default) for col in cols]
            for i, row in enumerate(rows):
                rows[i] = [fmt(col) for fmt, col in zip(formats, row)]

        data['query'] = sql
        data['error'] = error
        data['cols'] = cols
        data['rows'] = rows
        data['took'] = took
        data['raw'] = raw

        return 'sql.html', data, None

    def _process_schema(self, req, cursor, data):

        if self.db_type == 'mysql':
            sql = 'show tables'
        elif self.db_type == 'sqlite':
            sql = 'SELECT name FROM sqlite_master WHERE type = "table"'
        else:
            assert False, "Unsupported db_type: %s" % self.db_type

        cursor.execute(sql)
        rows = cursor.fetchall()

        table = req.args.get('table', '')
        valid = False

        tables = []
        for x, in sorted(rows):
            if x == table:
                valid = True
                tables.append(html.B(x))
            else:
                tables.append(html.A(x, href=req.href.sql('schema', table=x)))

        if table and valid:
            if self.db_type == 'mysql':
                sql = 'describe %s' % table
            elif self.db_type == 'sqlite':
                sql = 'PRAGMA table_info("%s")' % table
            else:
                assert False, "Unsupported db_type: %s" % self.db_type

            cursor.execute(sql)
            cols = map(lambda x: x[0], cursor.description)
            rows = cursor.fetchall()

            cursor.execute("select count(*) from %s" % table)
            count, = cursor.fetchall()[0]
        else:
            cols = rows = []
            count = 0

        data['tables'] = tables
        data['cols'] = cols
        data['rows'] = rows
        data['table'] = table
        data['count'] = count

        # FIXME: Add index list?
        # FIXME: Add foreign key list?

        return 'schema.html', data, None


