import sqlite3

from db_cache import DBCache


class SQLiteCache(DBCache):

    def __init__(self, dbpath, table='cache'):
        self.dbpath = dbpath
        self.table = table
        super(SQLiteCache, self).__init__()

    def connect(self):
        return sqlite3.connect(self.dbpath)

    def init_db(self):
        create_sql = '''CREATE TABLE IF NOT EXISTS `%s` (
          key PRIMARY KEY, value
        )''' % self.table
        print('Creating db')
        with self.connection() as conn:
            print('created table: %s' % self.table)
            conn.execute(create_sql)
