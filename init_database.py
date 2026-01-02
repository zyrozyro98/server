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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            registration_date TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # جدول التراخيص
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE,
            customer_id INTEGER,
            start_date TEXT,
            expiry_date TEXT,
            plan_type TEXT,
            max_devices INTEGER DEFAULT 1,
            devices_registered INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # جدول الأجهزة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE,
            machine_id TEXT,
            device_name TEXT,
            license_key TEXT,
            registration_date TEXT,
            last_active TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (license_key) REFERENCES licenses (license_key)
        )
    ''')
    
    # جدول الاستخدام
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT,
            device_id TEXT,
            action_type TEXT,
            details TEXT,
            timestamp TEXT,
            FOREIGN KEY (license_key) REFERENCES licenses (license_key)
        )
    ''')
    
    # إضافة بيانات تجريبية
    add_sample_data(cursor)
    
    conn.commit()
    conn.close()
    
    print("✅ تم إنشاء قاعدة البيانات بنجاح!")
    print("📊 يمكنك الآن تشغيل السيرفر")

def add_sample_data(cursor):
    """إضافة بيانات تجريبية"""
    # إضافة عملاء
    customers = [
        ('يوسف محمد زهير', 'yousef@example.com', '967771831482', '2024-01-01'),
        ('أحمد علي', 'ahmed@example.com', '966500123456', '2024-01-15'),
        ('محمد سعيد', 'mohamed@example.com', '201001234567', '2024-02-01')
    ]
    
    for customer in customers:
        cursor.execute('''
            INSERT OR IGNORE INTO customers (name, email, phone, registration_date)
            VALUES (?, ?, ?, ?)
        ''', customer)
    
    # إضافة تراخيص
    licenses = [
        ('TEST-LICENSE-2024-ABCD', 1, '2024-01-01', '2024-12-31', 'premium', 5),
        ('LIC-1A2B3C4D-202401', 2, '2024-01-15', '2024-04-15', 'standard', 2),
        ('LIC-5E6F7G8H-202402', 3, '2024-02-01', '2024-03-01', 'basic', 1)
    ]
    
    for license in licenses:
        cursor.execute('''
            INSERT OR IGNORE INTO licenses 
            (license_key, customer_id, start_date, expiry_date, plan_type, max_devices)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', license)
    
    print("📝 تم إضافة بيانات تجريبية")

if __name__ == "__main__":
    init_database()
