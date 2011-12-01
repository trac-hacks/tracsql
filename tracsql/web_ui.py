
# stdlib imports
import re
import time

# trac imports
import trac
from trac.core import *
from trac.db.api import DatabaseManager
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

    def get_db_cnx(self):
        """
        Load the database, either user-specified or the project database.
        """
        db_str = self.env.config.get('tracsql', 'database', '')

        if db_str:
            class ExternalDatabaseManager(DatabaseManager):
                connection_uri = db_str
            db_mgr = ExternalDatabaseManager(self.env)
            db = db_mgr.get_connection()

        else:
            db_str = self.env.config.get('trac', 'database')
            db = self.env.get_db_cnx()

        return db, db_str

    def process_request(self, req):
        req.perm.require('TRAC_ADMIN')

        path = req.args.get('path', '')

        data = {}

        db, db_str = self.get_db_cnx()
        cursor = db.cursor()
        db_type, db_path = db_str.split(':', 1)
        assert db_type in ('sqlite', 'mysql', 'postgres'), \
                            'Unsupported database "%s"' % db_type
        self.db_type = db_type

        # Include trac wiki stylesheet
        add_stylesheet(req, 'common/css/wiki.css')

        # Include trac stats stylesheet
        add_stylesheet(req, 'sql/common.css')

        # Include javascript libraries
        add_script(req, 'stats/jquery-1.6.3.min.js')

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
        csv = req.args.get('csv', '')

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
            except e:
                error = e

        if csv:
            text = []
            for col in cols:
                text.append('%s,' % col)
            text.append('\n')
            for row in rows:
                for cell in row:
                    text.append("%s," % cell)
                text.append('\n')
            text = str(''.join(text))
            req.send_response(200)
            req.send_header('Content-Type', 'text/csv')
            req.send_header('Content-Length', str(len(text)))
            req.end_headers()
            req.write(text)
            return

        if not raw:

            format = {
                'path' : lambda x: html.A(x, href=req.href.browser(x)),
                'rev' : lambda x: html.A(x, href=req.href.changeset(x)),
                'ticket' : lambda x: html.A(x, href=req.href.ticket(x)),
                'query' : lambda x: html.PRE(x, style="padding: 0; margin: 0;"),
                'time' : lambda x: fmt_timestamp(x),
            }

            if trac.__version__.startswith('0.12'):
                format['time'] = lambda x: fmt_timestamp(x/1000000.)

            format['base_path'] = format['path']
            format['base_rev'] = format['rev']
            format['changetime'] = format['time']

            def format_wiki_text(text):
                from trac.mimeview.api import Mimeview
                mimeview = Mimeview(self.env)
                mimetype = 'text/x-trac-wiki'
                return mimeview.render(req, mimetype, text)

            if re.search('.*from wiki.*', sql, re.IGNORECASE|re.MULTILINE):
                format['name'] = lambda x: html.A(x, href=req.href.wiki(x))
                format['text'] = format_wiki_text
            elif re.search('.*from ticket.*', sql, re.IGNORECASE|re.MULTILINE):
                format['id'] = lambda x: html.A(x, href=req.href.ticket(x))
                format['component'] = lambda x: html.A(x, href=req.href.query(component=x))
                format['severity'] = lambda x: html.A(x, href=req.href.query(severity=x))
                format['type'] = lambda x: html.A(x, href=req.href.query(type=x))
                format['milestone'] = lambda x: html.A(x, href=req.href.query(milestone=x))
                format['version'] = lambda x: html.A(x, href=req.href.query(version=x))
                format['status'] = lambda x: html.A(x, href=req.href.query(status=x))
                format['owner'] = lambda x: html.A(x, href=req.href.query(owner=x))
                format['reporter'] = lambda x: html.A(x, href=req.href.query(reporter=x))
                format['priority'] = lambda x: html.A(x, href=req.href.query(priority=x))
                format['resolution'] = lambda x: html.A(x, href=req.href.query(resolution=x))
            elif re.search('.*from report.*', sql, re.IGNORECASE|re.MULTILINE):
                format['id'] = lambda x: html.A(x, href=req.href.report(x))

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
        elif self.db_type == 'postgres':
            sql = "select table_name from information_schema.tables where table_schema = 'public'"
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
            cols = ["name", "type", "nullable", "default"]
            if self.db_type == 'mysql':
                sql = 'describe %s' % table
                cursor.execute(sql)
                results = cursor.fetchall()
                rows = []
                for field, type, null, key, default, extra in results:
                    rows.append((field, type, null, default))
            elif self.db_type == 'sqlite':
                sql = 'PRAGMA table_info("%s")' % table
                cursor.execute(sql)
                results = cursor.fetchall()
                rows = []
                for cid, name, type, notnull, dflt_value, pk in results:
                    rows.append((name, type, notnull, dflt_value))
            elif self.db_type == 'postgres':
                sql = """
                select
                  column_name,
                  data_type,
                  is_nullable,
                  column_default
                from information_schema.columns
                where table_schema = 'public' and
                      table_name = '%s'
                """ % table
                cursor.execute(sql)
                rows = cursor.fetchall()
            else:
                assert False, "Unsupported db_type: %s" % self.db_type


            cursor.execute("select count(*) from %s" % table)
            count, = cursor.fetchall()[0]

            if self.db_type == 'mysql':
                sql = """
                select
                    index_name,
                    group_concat(column_name
                                 order by seq_in_index
                                 separator ", ")
                from information_schema.statistics
                where table_name = '%s'
                group by index_name
                """ % table
                cursor.execute(sql)
                indexes = cursor.fetchall()
            elif self.db_type == 'sqlite':
                sql = """
                select name
                from sqlite_master
                where tbl_name = '%s'
                  and type = 'index'
                """ % table
                cursor.execute(sql)
                results = cursor.fetchall()
                indexes = []
                for index, in results:
                    cursor.execute("PRAGMA index_info('%s')" % index)
                    indexes.append((index, ", ".join(name for _, _, name in
                                                     cursor.fetchall())))
            elif self.db_type == 'postgres':
                sql = "select indexname, indexdef from pg_indexes where tablename = '%s'" % table
                cursor.execute(sql)
                indexes = cursor.fetchall()
            else:
                assert False, "Unsupported db_type: %s" % self.db_type

        else:
            cols = rows = []
            count = 0
            indexes = []

        data['tables'] = tables
        data['table'] = table
        data['cols'] = cols
        data['rows'] = rows
        data['count'] = count
        data['indexes'] = indexes

        # FIXME: Add foreign key list?

        return 'schema.html', data, None


