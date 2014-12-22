from threading import RLock
from contextlib import contextmanager

from ..cache import BaseCache


class DBCache(BaseCache):

    def __init__(self):
        self._lock = RLock()
        self.init_db()

    def connect(self):
        raise NotImplemented

    def init_db(self):
        raise NotImplemented

    @contextmanager
    def connection(self):
        with self._lock:
            conn = self.connect()
            yield conn
            conn.commit()
            conn.close()

    def get(self, key):
        with self.connection() as conn:
            sql = 'SELECT value FROM `%s` WHERE key = ?' % self.table
            print(sql)
            row = conn.execute('SELECT * FROM cache').fetchone()
            return None

            row = conn.execute(sql, (key,)).fetchone()
            print(row)
            if not row:
                return None
            return row[0]

    def set(self, key, fh):
        with self.connection() as conn:
            exists = self.get(key)
            sql = u'INSERT INTO `%s` (value, key) values (?, ?)' % self.table,

            if exists:
                sql = u'UPDATE `%s` SET value = ? WHERE key = ?' % self.table

            conn.execute(sql, (fh.read(), key))

    def delete(self, key):
        try:
            with self.connection() as conn:
                conn.execute(
                    u'DELETE FROM `%s` WHERE key = ?' % self.table,
                    (key,)
                )
        except:
            pass
