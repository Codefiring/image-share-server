import sqlite3
import secrets
from datetime import datetime
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            share_token TEXT UNIQUE NOT NULL,
            owner_ip TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            visibility TEXT DEFAULT 'public',
            allowed_ips TEXT,
            one_time INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def create_image(filename, owner_ip):
    conn = get_db()
    share_token = secrets.token_urlsafe(16)
    conn.execute(
        'INSERT INTO images (filename, share_token, owner_ip) VALUES (?, ?, ?)',
        (filename, share_token, owner_ip)
    )
    conn.commit()
    conn.close()
    return share_token

def get_image_by_token(token):
    conn = get_db()
    image = conn.execute(
        'SELECT * FROM images WHERE share_token = ?', (token,)
    ).fetchone()
    conn.close()
    return image
