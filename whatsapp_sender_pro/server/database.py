"""
إدارة قاعدة البيانات
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path='licenses.db'):
        self.db_path = db_path
        self.init_tables()

    def get_connection(self):
        """إنشاء اتصال بقاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self):
        """تهيئة الجداول"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # نفس الجداول من server.py
        tables = [
            '''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                phone TEXT,
                name TEXT,
                whatsapp_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT UNIQUE,
                user_id INTEGER,
                plan_type TEXT,
                license_type TEXT,
                status TEXT DEFAULT 'active',
                expiry_date TIMESTAMP,
                activation_date TIMESTAMP,
                hwid TEXT,
                max_devices INTEGER DEFAULT 1,
                activation_count INTEGER DEFAULT 0,
                features TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )''',

            '''CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                license_id INTEGER,
                amount REAL,
                currency TEXT DEFAULT 'USD',
                payment_method TEXT,
                transaction_id TEXT UNIQUE,
                receipt_image TEXT,
                status TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (license_id) REFERENCES licenses (id)
            )''',

            '''CREATE TABLE IF NOT EXISTS user_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                license_id INTEGER,
                hwid TEXT,
                device_info TEXT,
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (license_id) REFERENCES licenses (id)
            )''',

            '''CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                license_id INTEGER,
                action TEXT,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (license_id) REFERENCES licenses (id)
            )'''
        ]

        for table_sql in tables:
            try:
                cursor.execute(table_sql)
            except Exception as e:
                logger.error(f"خطأ في إنشاء الجدول: {e}")

        conn.commit()
        conn.close()

    # دوال CRUD للتراخيص
    def create_license(self, license_data: Dict) -> Optional[str]:
        """إنشاء رخصة جديدة"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO licenses (
                license_key, user_id, plan_type, license_type,
                expiry_date, max_devices, features
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                license_data['license_key'],
                license_data.get('user_id'),
                license_data.get('plan_type', 'premium'),
                license_data.get('license_type', 'monthly'),
                license_data.get('expiry_date'),
                license_data.get('max_devices', 1),
                json.dumps(license_data.get('features', {}))
            ))

            conn.commit()
            license_id = cursor.lastrowid
            conn.close()

            return license_id

        except Exception as e:
            logger.error(f"خطأ في إنشاء الرخصة: {e}")
            return None

    def get_license(self, license_key: str) -> Optional[Dict]:
        """الحصول على رخصة"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT l.*, u.email, u.name, u.whatsapp_number 
            FROM licenses l
            LEFT JOIN users u ON l.user_id = u.id
            WHERE l.license_key = ?
            ''', (license_key,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"خطأ في جلب الرخصة: {e}")
            return None

    def update_license(self, license_key: str, update_data: Dict) -> bool:
        """تحديث رخصة"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            set_clauses = []
            values = []

            for key, value in update_data.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)

            values.append(license_key)

            cursor.execute(f'''
            UPDATE licenses 
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE license_key = ?
            ''', values)

            conn.commit()
            conn.close()

            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"خطأ في تحديث الرخصة: {e}")
            return False

    def delete_license(self, license_key: str) -> bool:
        """حذف رخصة"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM licenses WHERE license_key = ?', (license_key,))

            conn.commit()
            success = cursor.rowcount > 0
            conn.close()

            return success

        except Exception as e:
            logger.error(f"خطأ في حذف الرخصة: {e}")
            return False

    # دوال CRUD للمستخدمين
    def create_user(self, user_data: Dict) -> Optional[int]:
        """إنشاء مستخدم جديد"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO users (email, phone, name, whatsapp_number)
            VALUES (?, ?, ?, ?)
            ''', (
                user_data.get('email'),
                user_data.get('phone'),
                user_data.get('name'),
                user_data.get('whatsapp_number')
            ))

            conn.commit()
            user_id = cursor.lastrowid
            conn.close()

            return user_id

        except Exception as e:
            logger.error(f"خطأ في إنشاء المستخدم: {e}")
            return None

    def get_user(self, email: str) -> Optional[Dict]:
        """الحصول على مستخدم"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"خطأ في جلب المستخدم: {e}")
            return None

    # دوال إدارة الأجهزة
    def add_device(self, device_data: Dict) -> bool:
        """إضافة جهاز"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO user_devices (user_id, license_id, hwid, device_info)
            VALUES (?, ?, ?, ?)
            ''', (
                device_data.get('user_id'),
                device_data.get('license_id'),
                device_data.get('hwid'),
                json.dumps(device_data.get('device_info', {}))
            ))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"خطأ في إضافة الجهاز: {e}")
            return False

    def get_device_count(self, license_id: int) -> int:
        """الحصول على عدد أجهزة الرخصة"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT COUNT(*) as count 
            FROM user_devices 
            WHERE license_id = ?
            ''', (license_id,))

            result = cursor.fetchone()
            conn.close()

            return result['count'] if result else 0

        except Exception as e:
            logger.error(f"خطأ في جلب عدد الأجهزة: {e}")
            return 0

    # دوال التقارير والإحصائيات
    def get_license_stats(self) -> Dict:
        """الحصول على إحصائيات التراخيص"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
                SUM(CASE WHEN status = 'suspended' THEN 1 ELSE 0 END) as suspended
            FROM licenses
            ''')

            result = cursor.fetchone()
            conn.close()

            return dict(result) if result else {}

        except Exception as e:
            logger.error(f"خطأ في جلب إحصائيات التراخيص: {e}")
            return {}

    def get_recent_activity(self, limit: int = 50) -> List[Dict]:
        """الحصول على النشاطات الحديثة"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT a.*, u.email, l.license_key
            FROM activity_logs a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN licenses l ON a.license_id = l.id
            ORDER BY a.created_at DESC
            LIMIT ?
            ''', (limit,))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"خطأ في جلب النشاطات: {e}")
            return []

    def log_activity(self, activity_data: Dict) -> bool:
        """تسجيل نشاط"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO activity_logs 
            (user_id, license_id, action, details, ip_address)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                activity_data.get('user_id'),
                activity_data.get('license_id'),
                activity_data.get('action'),
                json.dumps(activity_data.get('details', {})),
                activity_data.get('ip_address')
            ))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"خطأ في تسجيل النشاط: {e}")
            return False