import psycopg2

# Database connection configuration
DB_NAME = "bank_app"
DB_USER = "bank_user"
DB_PASSWORD = "CSCI430_CTF1_KANMJA"
DB_HOST = "localhost"

def get_db_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST
    )
    return conn

def get_user_from_cookie(cookie):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT users.id, users.username FROM sessions JOIN users ON sessions.user_id = users.id WHERE sessions.cookie = %s;", (cookie,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    return user_data

