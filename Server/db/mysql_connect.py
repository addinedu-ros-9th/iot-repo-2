import sys
sys.path.append('/home/tunguser/iot_project')

from mysql.connector import pooling
from server.config import DB_CONFIG

pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    **DB_CONFIG
)

def get_connection():
    return pool.get_connection()