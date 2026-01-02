"""
🔐 سيرفر إدارة الاشتراكات - مرسل واتساب الاحترافي
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import hashlib
import sqlite3
import os
from typing import Dict, List, Any

app = Flask(__name__)
CORS(app)  # تمكين CORS للاتصال من التطبيق

# إعدادات قاعدة البيانات
DATABASE_FILE = "subscriptions.db"
API_KEY = "YES2Z8924_0"

def init_database():
    """تهيئة قاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_FILE)
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
    
    conn.commit()
    conn.close()
    
    # إضافة ترخيص تجريبي للمطور
    add_test_licenses()

def add_test_licenses():
    """إضافة تراخيص تجريبية"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # التحقق إذا كان المطور موجود
    cursor.execute("SELECT id FROM customers WHERE email = 'yousef@example.com'")
    if not cursor.fetchone():
        # إضافة المطور
        cursor.execute('''
            INSERT INTO customers (name, email, phone, registration_date)
            VALUES (?, ?, ?, ?)
        ''', ('يوسف محمد زهير', 'yousef@example.com', '967771831482', datetime.now().isoformat()))
        
        customer_id = cursor.lastrowid
        
        # إضافة ترخيص تجريبي لمدة سنة
        license_key = "TEST-LICENSE-2024-ABCD"
        expiry_date = (datetime.now() + timedelta(days=365)).isoformat()
        
        cursor.execute('''
            INSERT INTO licenses (license_key, customer_id, start_date, expiry_date, plan_type, max_devices)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (license_key, customer_id, datetime.now().isoformat(), expiry_date, 'premium', 5))
        
        conn.commit()
    
    conn.close()

def verify_api_key():
    """التحقق من مفتاح API"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False
    
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        return token == API_KEY
    
    return False

@app.route('/api/v1/subscription/validate', methods=['POST'])
def validate_subscription():
    """التحقق من صحة الاشتراك"""
    if not verify_api_key():
        return jsonify({
            'success': False,
            'message': 'غير مصرح به',
            'error_code': 'UNAUTHORIZED'
        }), 401
    
    try:
        data = request.json
        machine_id = data.get('machine_id')
        
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # البحث عن الجهاز
        cursor.execute('''
            SELECT d.license_key, l.expiry_date, l.plan_type, l.max_devices, 
                   l.devices_registered, l.status, d.device_id
            FROM devices d
            JOIN licenses l ON d.license_key = l.license_key
            WHERE d.machine_id = ? AND d.is_active = 1 AND l.status = 'active'
        ''', (machine_id,))
        
        device_data = cursor.fetchone()
        
        if not device_data:
            return jsonify({
                'success': False,
                'message': 'الجهاز غير مسجل أو الرخصة غير صالحة',
                'error_code': 'DEVICE_NOT_FOUND'
            })
        
        license_key, expiry_date, plan_type, max_devices, devices_registered, status, device_id = device_data
        
        # التحقق من تاريخ الانتهاء
        expiry_datetime = datetime.fromisoformat(expiry_date)
        if expiry_datetime < datetime.now():
            return jsonify({
                'success': False,
                'message': 'انتهت فترة الاشتراك',
                'error_code': 'LICENSE_EXPIRED'
            })
        
        # تحديث آخر نشاط
        cursor.execute('''
            UPDATE devices SET last_active = ? WHERE machine_id = ?
        ''', (datetime.now().isoformat(), machine_id))
        
        conn.commit()
        conn.close()
        
        remaining_days = (expiry_datetime - datetime.now()).days
        
        return jsonify({
            'success': True,
            'message': 'الاشتراك ساري المفعول',
            'data': {
                'license_key': license_key,
                'expiry_date': expiry_date,
                'remaining_days': remaining_days,
                'plan_type': plan_type,
                'max_devices': max_devices,
                'devices_registered': devices_registered,
                'device_id': device_id
            },
            'session_token': hashlib.sha256(f"{license_key}{machine_id}{datetime.now().isoformat()}".encode()).hexdigest()[:32]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في الخادم: {str(e)}',
            'error_code': 'SERVER_ERROR'
        }), 500

@app.route('/api/v1/subscription/activate', methods=['POST'])
def activate_license():
    """تفعيل مفتاح الترخيص"""
    if not verify_api_key():
        return jsonify({
            'success': False,
            'message': 'غير مصرح به',
            'error_code': 'UNAUTHORIZED'
        }), 401
    
    try:
        data = request.json
        license_key = data.get('license_key')
        machine_id = data.get('machine_id')
        device_name = data.get('device_name', 'Unknown Device')
        
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # التحقق من صحة الترخيص
        cursor.execute('''
            SELECT l.*, c.name as customer_name 
            FROM licenses l
            JOIN customers c ON l.customer_id = c.id
            WHERE l.license_key = ? AND l.status = 'active'
        ''', (license_key,))
        
        license_data = cursor.fetchone()
        
        if not license_data:
            return jsonify({
                'success': False,
                'message': 'مفتاح الترخيص غير صالح',
                'error_code': 'INVALID_LICENSE'
            })
        
        # الحصول على أسماء الأعمدة
        columns = [description[0] for description in cursor.description]
        license_dict = dict(zip(columns, license_data))
        
        # التحقق من تاريخ الانتهاء
        expiry_date = datetime.fromisoformat(license_dict['expiry_date'])
        if expiry_date < datetime.now():
            return jsonify({
                'success': False,
                'message': 'انتهت فترة الاشتراك',
                'error_code': 'LICENSE_EXPIRED'
            })
        
        # التحقق من عدد الأجهزة المسموح بها
        if license_dict['devices_registered'] >= license_dict['max_devices']:
            return jsonify({
                'success': False,
                'message': 'تم الوصول إلى الحد الأقصى للأجهزة',
                'error_code': 'MAX_DEVICES_REACHED'
            })
        
        # التحقق إذا كان الجهاز مسجلاً مسبقاً
        cursor.execute('SELECT id FROM devices WHERE machine_id = ?', (machine_id,))
        existing_device = cursor.fetchone()
        
        if existing_device:
            # تحديث الجهاز الحالي
            cursor.execute('''
                UPDATE devices 
                SET license_key = ?, last_active = ?, is_active = 1 
                WHERE machine_id = ?
            ''', (license_key, datetime.now().isoformat(), machine_id))
        else:
            # تسجيل جهاز جديد
            device_id = f"DEV-{hashlib.sha256(f'{license_key}{machine_id}'.encode()).hexdigest()[:8]}"
            
            cursor.execute('''
                INSERT INTO devices (device_id, machine_id, device_name, license_key, registration_date, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (device_id, machine_id, device_name, license_key, 
                  datetime.now().isoformat(), datetime.now().isoformat()))
            
            # تحديث عدد الأجهزة المسجلة
            cursor.execute('''
                UPDATE licenses 
                SET devices_registered = devices_registered + 1 
                WHERE license_key = ?
            ''', (license_key,))
        
        conn.commit()
        
        # الحصول على البيانات المحدثة
        cursor.execute('''
            SELECT device_id FROM devices WHERE machine_id = ?
        ''', (machine_id,))
        
        new_device_id = cursor.fetchone()[0]
        
        remaining_days = (expiry_date - datetime.now()).days
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'تم تفعيل الترخيص بنجاح',
            'data': {
                'license_key': license_key,
                'customer_name': license_dict['customer_name'],
                'start_date': license_dict['start_date'],
                'expiry_date': license_dict['expiry_date'],
                'remaining_days': remaining_days,
                'plan_type': license_dict['plan_type'],
                'device_id': new_device_id,
                'max_devices': license_dict['max_devices'],
                'devices_registered': license_dict['devices_registered'] + 1
            },
            'session_token': hashlib.sha256(f"{license_key}{machine_id}{datetime.now().isoformat()}".encode()).hexdigest()[:32]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في التفعيل: {str(e)}',
            'error_code': 'ACTIVATION_ERROR'
        }), 500

@app.route('/api/v1/usage/log', methods=['POST'])
def log_usage():
    """تسجيل استخدام التطبيق"""
    if not verify_api_key():
        return jsonify({
            'success': False,
            'message': 'غير مصرح به'
        }), 401
    
    try:
        data = request.json
        license_key = data.get('license_key')
        device_id = data.get('device_id')
        action_type = data.get('action_type')
        details = data.get('details', '')
        
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO usage_logs (license_key, device_id, action_type, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (license_key, device_id, action_type, details, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'تم تسجيل الاستخدام'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في التسجيل: {str(e)}'
        }), 500

@app.route('/api/v1/licenses/create', methods=['POST'])
def create_license():
    """إنشاء ترخيص جديد (للوحة التحكم)"""
    if not verify_api_key():
        return jsonify({
            'success': False,
            'message': 'غير مصرح به'
        }), 401
    
    try:
        data = request.json
        customer_email = data.get('customer_email')
        plan_type = data.get('plan_type', 'basic')
        duration_days = data.get('duration_days', 30)
        max_devices = data.get('max_devices', 1)
        
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # البحث عن العميل
        cursor.execute('SELECT id FROM customers WHERE email = ?', (customer_email,))
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({
                'success': False,
                'message': 'العميل غير موجود'
            })
        
        customer_id = customer[0]
        
        # إنشاء مفتاح ترخيص فريد
        import secrets
        license_key = f"LIC-{secrets.token_hex(8).upper()}-{datetime.now().strftime('%Y%m')}"
        
        start_date = datetime.now()
        expiry_date = start_date + timedelta(days=duration_days)
        
        cursor.execute('''
            INSERT INTO licenses (license_key, customer_id, start_date, expiry_date, plan_type, max_devices)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (license_key, customer_id, start_date.isoformat(), 
              expiry_date.isoformat(), plan_type, max_devices))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء الترخيص',
            'license_key': license_key,
            'expiry_date': expiry_date.isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في إنشاء الترخيص: {str(e)}'
        }), 500

@app.route('/api/v1/admin/licenses', methods=['GET'])
def get_all_licenses():
    """الحصول على جميع التراخيص (للوحة التحكم)"""
    if not verify_api_key():
        return jsonify({
            'success': False,
            'message': 'غير مصرح به'
        }), 401
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT l.license_key, c.name, c.email, l.start_date, 
                   l.expiry_date, l.plan_type, l.status, l.devices_registered,
                   l.max_devices
            FROM licenses l
            JOIN customers c ON l.customer_id = c.id
            ORDER BY l.created_at DESC
        ''')
        
        licenses = cursor.fetchall()
        conn.close()
        
        result = []
        for license in licenses:
            result.append({
                'license_key': license[0],
                'customer_name': license[1],
                'customer_email': license[2],
                'start_date': license[3],
                'expiry_date': license[4],
                'plan_type': license[5],
                'status': license[6],
                'devices_registered': license[7],
                'max_devices': license[8],
                'is_expired': datetime.fromisoformat(license[4]) < datetime.now() if license[4] else True
            })
        
        return jsonify({
            'success': True,
            'licenses': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في جلب البيانات: {str(e)}'
        }), 500

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """فحص حالة السيرفر"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    # تهيئة قاعدة البيانات
    init_database()
    
    # تشغيل السيرفر
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
