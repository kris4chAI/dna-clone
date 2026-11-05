import os
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sactakeoff:sactakeoff@localhost:5432/sactakeoff")

pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, kwargs={"row_factory": dict_row}, open=False)


@contextmanager
def conn():
    with pool.connection() as c:
        yield c


def q(sql, params=None):
    with conn() as c:
        return c.execute(sql, params or ()).fetchall()


def one(sql, params=None):
    with conn() as c:
        return c.execute(sql, params or ()).fetchone()


def run(sql, params=None):
    with conn() as c:
        cur = c.execute(sql, params or ())
        try:
            return cur.fetchone()
        except Exception:
            return None
