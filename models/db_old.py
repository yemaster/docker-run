import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB

from config import Config

from utils.auth import hash_password

db_pool = PooledDB(
    creator=pymysql,
    mincached=1,
    maxcached=5,
    maxconnections=10,
    blocking=True,
    host=Config.DB_HOST,
    user=Config.DB_USER,
    password=Config.DB_PASS,
    database=Config.DB_NAME,
    port=Config.DB_PORT,
    charset='utf8mb4',
    cursorclass=DictCursor
)

def execute_query(sql, args=None):
    with db_pool.connection() as conn:
        with conn.cursor() as cursor:
            if args is None:
                cursor.execute(sql)
            else:
                cursor.execute(sql, args)
            if sql.strip().upper().startswith("SELECT"):
                res = cursor.fetchall()
                return res
            else:
                conn.commit()
                if sql.strip().upper().startswith("INSERT"):
                    return cursor.lastrowid
                return cursor.rowcount

def select_one(sql, args=None):
    with db_pool.connection() as conn:
        with conn.cursor() as cursor:
            if args is None:
                cursor.execute(sql)
            else:
                cursor.execute(sql, args)
            return cursor.fetchone()

# ---- 初始化 ----
def init_db():
    execute_query('''
        CREATE TABLE IF NOT EXISTS admins (
            id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255)
        )
    ''')
    execute_query('''
        CREATE TABLE IF NOT EXISTS templates (
            id INT PRIMARY KEY AUTO_INCREMENT,
            description TEXT,
            name VARCHAR(255),
            image VARCHAR(255),
            cpu_limit VARCHAR(50),
            mem_limit VARCHAR(50),
            disk_limit VARCHAR(50),
            command TEXT,
            available_command TEXT,
            tags TEXT,
            container_port INT
        )
    ''')
    execute_query('''
        CREATE TABLE IF NOT EXISTS containers (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255),
            user_id VARCHAR(255),
            template_id INT,
            docker_id VARCHAR(255),
            host_port INT,
            status VARCHAR(50),
            extended_times INT DEFAULT 0,
            destroy_time TIMESTAMP
        )
    ''')
    execute_query('''
        CREATE TABLE IF NOT EXISTS logs (
            id INT PRIMARY KEY AUTO_INCREMENT,
            action TEXT,
            user_id VARCHAR(255),
            timestamp TIMESTAMP
        )
    ''')
    hashed = hash_password(Config.ADMIN_PASSWORD)
    execute_query('INSERT IGNORE INTO admins (username, password_hash) VALUES (%s, %s)', (Config.ADMIN_USERNAME, hashed))

init_db()