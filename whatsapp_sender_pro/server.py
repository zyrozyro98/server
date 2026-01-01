"""
سيرفر إدارة التراخيص - WhatsApp Sender Pro
يعمل على Render.com
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import json
import hashlib
import uuid
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, Any, Optional, Tuple
import logging
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# إعداد التطبيق
app = Flask(__name__)
CORS(app)

# Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# مفتاح API السري
API_KEYS = {
    "WhatsApp_Sender_Pro_v2": os.getenv("API_SECRET", "default_secret_key_12345")
}

# إعدادات قاعدة البيانات
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://whatsapp_user:Nnfq2JfgR9A9yxLpk8pAOTP01G18MDUq@dpg-d5bejb15pdvs73bhp0gg-a/whatsapp_licenses')


def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    if DATABASE_URL.startswith('postgresql'):
        # PostgreSQL على Render
        import psycopg2
        import urllib.parse as urlparse
        url = urlparse.urlparse(DATABASE_URL)

        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
    else:
        # SQLite للتطوير المحلي
        conn = sqlite3.connect('licenses.db')
        conn.row_factory = sqlite3.Row

    return conn


def init_database():
    """تهيئة قاعدة البيانات"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # جدول المستخدمين
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE,
        phone VARCHAR(20),
        name VARCHAR(255),
        whatsapp_number VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # جدول التراخيص
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS licenses (
        id SERIAL PRIMARY KEY,
        license_key VARCHAR(255) UNIQUE,
        user_id INTEGER REFERENCES users(id),
        plan_type VARCHAR(50),
        license_type VARCHAR(50),
        status VARCHAR(50) DEFAULT 'active',
        expiry_date TIMESTAMP,
        activation_date TIMESTAMP,
        hwid TEXT,
        max_devices INTEGER DEFAULT 1,
        activation_count INTEGER DEFAULT 0,
        features JSONB,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # جدول المدفوعات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        license_id INTEGER REFERENCES licenses(id),
        amount DECIMAL(10, 2),
        currency VARCHAR(10) DEFAULT 'USD',
        payment_method VARCHAR(50),
        transaction_id VARCHAR(255) UNIQUE,
        receipt_image TEXT,
        status VARCHAR(50),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # جدول أجهزة المستخدمين
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_devices (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        license_id INTEGER REFERENCES licenses(id),
        hwid VARCHAR(255),
        device_info JSONB,
        last_seen TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # جدول السجل
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        license_id INTEGER REFERENCES licenses(id),
        action VARCHAR(100),
        details JSONB,
        ip_address VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()
    logger.info("✅ تم تهيئة قاعدة البيانات")


# تهيئة قاعدة البيانات عند البدء
init_database()


# ========================================================================
# Middleware والتحقق
# ========================================================================

def require_api_key(f):
    """ميدلوير للتحقق من مفتاح API"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.json.get('api_key')

        if not api_key:
            return jsonify({
                "success": False,
                "message": "مفتاح API مطلوب"
            }), 401

        if api_key not in API_KEYS.values():
            return jsonify({
                "success": False,
                "message": "مفتاح API غير صالح"
            }), 401

        return f(*args, **kwargs)

    return decorated_function


def log_activity(user_id=None, license_id=None, action="", details=None):
    """تسجيل النشاطات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        ip_address = request.remote_addr

        cursor.execute('''
        INSERT INTO activity_logs (user_id, license_id, action, details, ip_address)
        VALUES (%s, %s, %s, %s, %s)
        ''', (user_id, license_id, action, json.dumps(details or {}), ip_address))

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في تسجيل النشاط: {e}")


# ========================================================================
# واجهات API
# ========================================================================

@app.route('/')
def home():
    """الصفحة الرئيسية"""
    return jsonify({
        "status": "online",
        "service": "WhatsApp Sender Pro License Server",
        "version": "2.0.0",
        "developer": "يوسف محمد زهير",
        "support": "771831482"
    })


@app.route('/api/status')
def status():
    """فحص حالة السيرفر"""
    return jsonify({
        "success": True,
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    })


@app.route('/api/license/validate', methods=['POST'])
@require_api_key
@limiter.limit("30 per minute")
def validate_license():
    """التحقق من صحة الرخصة"""
    try:
        data = request.json
        license_key = data.get('license_key')
        hwid = data.get('hwid')
        app_id = data.get('app_id')

        if not all([license_key, hwid, app_id]):
            return jsonify({
                "success": False,
                "message": "بيانات غير كافية"
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # البحث عن الرخصة
        cursor.execute('''
        SELECT l.*, u.email, u.name, u.whatsapp_number 
        FROM licenses l
        LEFT JOIN users u ON l.user_id = u.id
        WHERE l.license_key = %s AND l.status = 'active'
        ''', (license_key,))

        license_row = cursor.fetchone()

        if not license_row:
            conn.close()
            log_activity(None, None, "license_validation_failed", {"license_key": license_key})
            return jsonify({
                "success": False,
                "message": "الرخصة غير موجودة أو غير مفعلة"
            }), 404

        # التحقق من تاريخ الانتهاء
        expiry_date = license_row['expiry_date']
        if expiry_date and datetime.now() > expiry_date:
            # تحديث حالة الرخصة إلى منتهية
            cursor.execute('''
            UPDATE licenses SET status = 'expired' WHERE id = %s
            ''', (license_row['id'],))
            conn.commit()
            conn.close()

            log_activity(license_row['user_id'], license_row['id'], "license_expired", {})
            return jsonify({
                "success": False,
                "message": "الرخصة منتهية الصلاحية"
            }), 400

        # التحقق من عدد الأجهزة
        cursor.execute('''
        SELECT COUNT(*) as device_count FROM user_devices 
        WHERE license_id = %s
        ''', (license_row['id'],))

        device_count = cursor.fetchone()['device_count']
        max_devices = license_row['max_devices'] or 1

        if device_count >= max_devices:
            # التحقق إذا كان الجهاز مسجلاً مسبقاً
            cursor.execute('''
            SELECT id FROM user_devices 
            WHERE license_id = %s AND hwid = %s
            ''', (license_row['id'], hwid))

            existing_device = cursor.fetchone()

            if not existing_device:
                conn.close()
                log_activity(license_row['user_id'], license_row['id'], "max_devices_reached", {})
                return jsonify({
                    "success": False,
                    "message": "تم تجاوز الحد الأقصى للأجهزة"
                }), 400

        # تسجيل/تحديث الجهاز
        cursor.execute('''
        SELECT id FROM user_devices 
        WHERE license_id = %s AND hwid = %s
        ''', (license_row['id'], hwid))

        existing_device = cursor.fetchone()

        if existing_device:
            # تحديث وقت آخر ظهور
            cursor.execute('''
            UPDATE user_devices SET last_seen = %s 
            WHERE id = %s
            ''', (datetime.now(), existing_device['id']))
        else:
            # تسجيل جهاز جديد
            cursor.execute('''
            INSERT INTO user_devices (user_id, license_id, hwid, device_info, last_seen)
            VALUES (%s, %s, %s, %s, %s)
            ''', (
                license_row['user_id'],
                license_row['id'],
                hwid,
                json.dumps(data.get('system_info', {})),
                datetime.now()
            ))

        # تحديث عدد التفعيلات
        cursor.execute('''
        UPDATE licenses 
        SET activation_count = activation_count + 1,
            updated_at = %s,
            hwid = %s
        WHERE id = %s
        ''', (datetime.now(), hwid, license_row['id']))

        conn.commit()

        # تحضير بيانات الرخصة للعودة
        license_data = {
            "license_key": license_row['license_key'],
            "plan": license_row['plan_type'],
            "type": license_row['license_type'],
            "status": license_row['status'],
            "expiry_date": license_row['expiry_date'].isoformat() if license_row['expiry_date'] else None,
            "activation_date": license_row['activation_date'].isoformat() if license_row['activation_date'] else None,
            "features": license_row['features'] or {},
            "max_devices": license_row['max_devices'],
            "hwid": hwid
        }

        conn.close()

        # تسجيل النشاط
        log_activity(
            license_row['user_id'],
            license_row['id'],
            "license_validated",
            {"hwid": hwid}
        )

        return jsonify({
            "success": True,
            "message": "الرخصة صالحة",
            "license_data": license_data
        })

    except Exception as e:
        logger.error(f"خطأ في التحقق من الرخصة: {e}")
        return jsonify({
            "success": False,
            "message": "حدث خطأ داخلي"
        }), 500


@app.route('/api/license/activate', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")
def activate_license():
    """تفعيل الرخصة"""
    try:
        data = request.json
        license_key = data.get('license_key')
        hwid = data.get('hwid')
        app_id = data.get('app_id')
        user_info = data.get('user_info', {})

        if not all([license_key, hwid, app_id]):
            return jsonify({
                "success": False,
                "message": "بيانات غير كافية"
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # البحث عن الرخصة
        cursor.execute('''
        SELECT l.* FROM licenses l
        WHERE l.license_key = %s
        ''', (license_key,))

        license_row = cursor.fetchone()

        if not license_row:
            conn.close()
            return jsonify({
                "success": False,
                "message": "الرخصة غير موجودة"
            }), 404

        # التحقق من حالة الرخصة
        if license_row['status'] != 'active':
            conn.close()
            return jsonify({
                "success": False,
                "message": f"الرخصة {license_row['status']}"
            }), 400

        # التحقق من تاريخ الانتهاء
        if license_row['expiry_date'] and datetime.now() > license_row['expiry_date']:
            cursor.execute('''
            UPDATE licenses SET status = 'expired' WHERE id = %s
            ''', (license_row['id'],))
            conn.commit()
            conn.close()

            return jsonify({
                "success": False,
                "message": "الرخصة منتهية الصلاحية"
            }), 400

        # التحقق من الأجهزة المسجلة
        cursor.execute('''
        SELECT COUNT(*) as device_count FROM user_devices 
        WHERE license_id = %s
        ''', (license_row['id'],))

        device_count = cursor.fetchone()['device_count']
        max_devices = license_row['max_devices'] or 1

        if device_count >= max_devices:
            # التحقق إذا كان الجهاز مسجلاً مسبقاً
            cursor.execute('''
            SELECT id FROM user_devices 
            WHERE license_id = %s AND hwid = %s
            ''', (license_row['id'], hwid))

            existing_device = cursor.fetchone()

            if not existing_device:
                conn.close()
                return jsonify({
                    "success": False,
                    "message": "تم تجاوز الحد الأقصى للأجهزة"
                }), 400

        # تسجيل/تحديث الجهاز
        cursor.execute('''
        SELECT id FROM user_devices 
        WHERE license_id = %s AND hwid = %s
        ''', (license_row['id'], hwid))

        existing_device = cursor.fetchone()

        if existing_device:
            # تحديث الجهاز
            cursor.execute('''
            UPDATE user_devices 
            SET device_info = %s, last_seen = %s 
            WHERE id = %s
            ''', (
                json.dumps(data.get('system_info', {})),
                datetime.now(),
                existing_device['id']
            ))
        else:
            # إنشاء مستخدم جديد إذا لزم الأمر
            if not license_row['user_id'] and user_info.get('email'):
                cursor.execute('''
                INSERT INTO users (email, name, whatsapp_number)
                VALUES (%s, %s, %s)
                RETURNING id
                ''', (
                    user_info.get('email'),
                    user_info.get('name', ''),
                    user_info.get('whatsapp', '')
                ))

                user_id = cursor.fetchone()['id']

                # ربط الرخصة بالمستخدم
                cursor.execute('''
                UPDATE licenses SET user_id = %s WHERE id = %s
                ''', (user_id, license_row['id']))
            else:
                user_id = license_row['user_id']

            # تسجيل جهاز جديد
            cursor.execute('''
            INSERT INTO user_devices (user_id, license_id, hwid, device_info, last_seen)
            VALUES (%s, %s, %s, %s, %s)
            ''', (
                user_id,
                license_row['id'],
                hwid,
                json.dumps(data.get('system_info', {})),
                datetime.now()
            ))

        # تحديث تاريخ التفعيل والـ HWID
        if not license_row['activation_date']:
            cursor.execute('''
            UPDATE licenses 
            SET activation_date = %s, hwid = %s,
                activation_count = activation_count + 1,
                updated_at = %s
            WHERE id = %s
            ''', (datetime.now(), hwid, datetime.now(), license_row['id']))
        else:
            cursor.execute('''
            UPDATE licenses 
            SET hwid = %s,
                activation_count = activation_count + 1,
                updated_at = %s
            WHERE id = %s
            ''', (hwid, datetime.now(), license_row['id']))

        conn.commit()

        # جلب الرخصة المحدثة
        cursor.execute('''
        SELECT * FROM licenses WHERE id = %s
        ''', (license_row['id'],))

        updated_license = cursor.fetchone()

        # تحضير بيانات الرخصة
        license_data = {
            "license_key": updated_license['license_key'],
            "plan": updated_license['plan_type'],
            "type": updated_license['license_type'],
            "status": updated_license['status'],
            "expiry_date": updated_license['expiry_date'].isoformat() if updated_license['expiry_date'] else None,
            "activation_date": updated_license['activation_date'].isoformat() if updated_license[
                'activation_date'] else None,
            "features": updated_license['features'] or {},
            "max_devices": updated_license['max_devices'],
            "hwid": hwid
        }

        conn.close()

        # تسجيل النشاط
        log_activity(
            user_id,
            license_row['id'],
            "license_activated",
            {"hwid": hwid, "app_id": app_id}
        )

        return jsonify({
            "success": True,
            "message": "تم تفعيل الرخصة بنجاح",
            "license_data": license_data
        })

    except Exception as e:
        logger.error(f"خطأ في تفعيل الرخصة: {e}")
        return jsonify({
            "success": False,
            "message": "حدث خطأ داخلي في التفعيل"
        }), 500


@app.route('/api/license/create', methods=['POST'])
@require_api_key
@limiter.limit("5 per minute")
def create_license():
    """إنشاء رخصة جديدة (للمسؤول)"""
    try:
        data = request.json

        # التحقق من الصلاحيات
        admin_key = data.get('admin_key')
        if admin_key != os.getenv('ADMIN_KEY', 'admin123'):
            return jsonify({
                "success": False,
                "message": "صلاحية غير كافية"
            }), 403

        # بيانات الرخصة
        plan_type = data.get('plan_type', 'premium')
        license_type = data.get('license_type', 'monthly')
        duration_days = data.get('duration_days', 30)
        max_devices = data.get('max_devices', 1)
        user_email = data.get('user_email')

        # إنشاء مفتاح فريد
        license_key = f"WS-{hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:12].upper()}"

        # حساب تاريخ الانتهاء
        expiry_date = datetime.now() + timedelta(days=duration_days)

        conn = get_db_connection()
        cursor = conn.cursor()

        # إنشاء أو جلب المستخدم
        user_id = None
        if user_email:
            cursor.execute('''
            SELECT id FROM users WHERE email = %s
            ''', (user_email,))

            user = cursor.fetchone()

            if user:
                user_id = user['id']
            else:
                # إنشاء مستخدم جديد
                cursor.execute('''
                INSERT INTO users (email, name)
                VALUES (%s, %s)
                RETURNING id
                ''', (user_email, data.get('user_name', '')))

                user_id = cursor.fetchone()['id']

        # إنشاء الرخصة
        cursor.execute('''
        INSERT INTO licenses (
            license_key, user_id, plan_type, license_type,
            expiry_date, max_devices, features
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        ''', (
            license_key,
            user_id,
            plan_type,
            license_type,
            expiry_date,
            max_devices,
            json.dumps(data.get('features', {
                "basic_sending": True,
                "unlimited_messages": True,
                "scheduling": True,
                "reports": True
            }))
        ))

        license_id = cursor.fetchone()['id']
        conn.commit()
        conn.close()

        # تسجيل النشاط
        log_activity(user_id, license_id, "license_created", {
            "plan_type": plan_type,
            "license_type": license_type,
            "duration_days": duration_days
        })

        return jsonify({
            "success": True,
            "message": "تم إنشاء الرخصة بنجاح",
            "license_key": license_key,
            "expiry_date": expiry_date.isoformat()
        })

    except Exception as e:
        logger.error(f"خطأ في إنشاء الرخصة: {e}")
        return jsonify({
            "success": False,
            "message": "حدث خطأ داخلي"
        }), 500


@app.route('/api/admin/licenses', methods=['GET'])
@require_api_key
def get_all_licenses():
    """الحصول على جميع التراخيص (للمسؤول)"""
    try:
        admin_key = request.args.get('admin_key')
        if admin_key != os.getenv('ADMIN_KEY', 'admin123'):
            return jsonify({
                "success": False,
                "message": "صلاحية غير كافية"
            }), 403

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT 
            l.id, l.license_key, l.plan_type, l.license_type,
            l.status, l.expiry_date, l.activation_date,
            l.activation_count, l.max_devices, l.created_at,
            u.email, u.name, u.whatsapp_number,
            COUNT(ud.id) as active_devices
        FROM licenses l
        LEFT JOIN users u ON l.user_id = u.id
        LEFT JOIN user_devices ud ON l.id = ud.license_id
        GROUP BY l.id, u.id
        ORDER BY l.created_at DESC
        ''')

        licenses = cursor.fetchall()
        conn.close()

        result = []
        for license_row in licenses:
            result.append({
                "id": license_row['id'],
                "license_key": license_row['license_key'],
                "plan_type": license_row['plan_type'],
                "license_type": license_row['license_type'],
                "status": license_row['status'],
                "expiry_date": license_row['expiry_date'].isoformat() if license_row['expiry_date'] else None,
                "activation_date": license_row['activation_date'].isoformat() if license_row[
                    'activation_date'] else None,
                "activation_count": license_row['activation_count'],
                "max_devices": license_row['max_devices'],
                "active_devices": license_row['active_devices'],
                "created_at": license_row['created_at'].isoformat(),
                "user_email": license_row['email'],
                "user_name": license_row['name'],
                "whatsapp_number": license_row['whatsapp_number']
            })

        return jsonify({
            "success": True,
            "licenses": result,
            "total": len(result)
        })

    except Exception as e:
        logger.error(f"خطأ في جلب التراخيص: {e}")
        return jsonify({
            "success": False,
            "message": "حدث خطأ داخلي"
        }), 500


@app.route('/api/admin/stats', methods=['GET'])
@require_api_key
def get_stats():
    """الحصول على إحصائيات النظام"""
    try:
        admin_key = request.args.get('admin_key')
        if admin_key != os.getenv('ADMIN_KEY', 'admin123'):
            return jsonify({
                "success": False,
                "message": "صلاحية غير كافية"
            }), 403

        conn = get_db_connection()
        cursor = conn.cursor()

        # إحصائيات التراخيص
        cursor.execute('''
        SELECT 
            COUNT(*) as total_licenses,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_licenses,
            SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired_licenses,
            SUM(CASE WHEN status = 'suspended' THEN 1 ELSE 0 END) as suspended_licenses
        FROM licenses
        ''')

        license_stats = cursor.fetchone()

        # إحصائيات المستخدمين
        cursor.execute('SELECT COUNT(*) as total_users FROM users')
        user_stats = cursor.fetchone()

        # إحصائيات المدفوعات
        cursor.execute('''
        SELECT 
            COUNT(*) as total_payments,
            SUM(amount) as total_revenue
        FROM payments 
        WHERE status = 'completed'
        ''')

        payment_stats = cursor.fetchone()

        # التراخيص التي ستنتهي خلال 7 أيام
        cursor.execute('''
        SELECT COUNT(*) as expiring_soon
        FROM licenses 
        WHERE status = 'active' 
        AND expiry_date BETWEEN NOW() AND NOW() + INTERVAL '7 days'
        ''')

        expiring_stats = cursor.fetchone()

        conn.close()

        return jsonify({
            "success": True,
            "stats": {
                "licenses": {
                    "total": license_stats['total_licenses'],
                    "active": license_stats['active_licenses'],
                    "expired": license_stats['expired_licenses'],
                    "suspended": license_stats['suspended_licenses'],
                    "expiring_soon": expiring_stats['expiring_soon']
                },
                "users": {
                    "total": user_stats['total_users']
                },
                "payments": {
                    "total": payment_stats['total_payments'] or 0,
                    "revenue": float(payment_stats['total_revenue'] or 0)
                }
            }
        })

    except Exception as e:
        logger.error(f"خطأ في جلب الإحصائيات: {e}")
        return jsonify({
            "success": False,
            "message": "حدث خطأ داخلي"
        }), 500


# ========================================================================
# نقطة الدخول
# ========================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('DEBUG', 'False') == 'True')
