import os

from psycopg.rows import dict_row
from psycopg.types.string import TextLoader
from psycopg_pool import ConnectionPool


def _configure(conn):
    # Cột NUMERIC (giá, tổng tiền) trả về dạng chuỗi "150000.00": tiền không đi qua số thực.
    conn.adapters.register_loader("numeric", TextLoader)


# Pool kết nối dùng chung. open=False: pool được mở khi ứng dụng khởi động (xem main.py).
pool = ConnectionPool(
    os.environ["DATABASE_URL"],
    min_size=1,
    max_size=10,
    open=False,
    kwargs={"row_factory": dict_row},
    configure=_configure,
)
