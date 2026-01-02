"""
🗄️ إعداد قاعدة البيانات الأولية
"""

import sqlite3
from datetime import datetime, timedelta
import json

def init_database():
    """تهيئة قاعدة البيانات"""
    conn = sqlite3.connect('subscriptions.db')
    cursor = conn.cursor()
    
    # جدول العملاء
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOIN
