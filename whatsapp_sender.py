"""
📱 WhatsApp Sender Professional v5.0
نظام إرسال رسائل واتساب تلقائي مع نظام اشتراكات شهري مربوط بالسيرفر
المطور: م/ يوسف محمد زهير - 771831482
"""

import os
import sys
import json
import time
import random
import pickle
import hashlib
import sqlite3
import threading
import platform
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# المكتبات التي تحتاج تثبيت
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, simpledialog
    from tkinter.ttk import Progressbar
    import requests
    import pyautogui
    import pyperclip
    import psutil
    import webbrowser
    from PIL import Image, ImageTk
    import csv
except ImportError as e:
    print(f"❌ المكتبات المطلوبة غير مثبتة: {e}")
    print("🔧 قم بتثبيت المكتبات باستخدام:")
    print("pip install tkinter requests pyautogui pyperclip psutil pillow")
    sys.exit(1)


# ================================================
# نظام الاشتراكات المرتبط بالسيرفر
# ================================================

class SecureSubscriptionManager:
    """مدير اشتراكات آمن مرتبط بالسيرفر"""

    def __init__(self):
        # إعدادات السيرفر
        self.SERVER_URL = "https://server-hxb7.onrender.com"
        self.API_KEY = "srv-d5bedjali9vc73bm33k0"
        self.API_URL = f"{self.SERVER_URL}/api/v1"

        # ملفات النظام
        self.LICENSE_FILE = "license.enc"
        self.DATABASE_FILE = "subscription.db"
        self.CONFIG_FILE = "app_config.ini"

        # معلمات الأمان
        self.APP_ID = "WHATSAPP_SENDER_PRO"
        self.APP_VERSION = "5.0.0"
        self.MAX_OFFLINE_DAYS = 3  # أقصى مدة للعمل بدون اتصال

        # معرف الجهاز
        self.machine_id = self._generate_machine_id()
        self.session_token = None

    def _generate_machine_id(self) -> str:
        """إنشاء معرف فريد للجهاز"""
        try:
            # جمع معلومات النظام
            system_info = {
                'hostname': platform.node(),
                'processor': platform.processor(),
                'system': platform.system(),
                'release': platform.release(),
                'machine': platform.machine(),
                'mac_address': self._get_mac_address()
            }

            # إنشاء هاش فريد
            info_string = json.dumps(system_info, sort_keys=True)
            machine_hash = hashlib.sha256(info_string.encode()).hexdigest()
            return f"{self.APP_ID}_{machine_hash[:16]}"

        except Exception:
            # استخدام معرف عشوائي كبديل
            import uuid
            return f"{self.APP_ID}_{uuid.uuid4().hex[:16]}"

    def _get_mac_address(self) -> str:
        """الحصول على عنوان MAC"""
        try:
            import uuid
            mac = uuid.getnode()
            return ':'.join(('%012X' % mac)[i:i + 2] for i in range(0, 12, 2))
        except:
            return "00:00:00:00:00:00"

    def initialize_system(self) -> bool:
        """تهيئة النظام"""
        try:
            # إنشاء المجلدات
            os.makedirs("data", exist_ok=True)
            os.makedirs("backups", exist_ok=True)
            os.makedirs("logs", exist_ok=True)

            # تهيئة قاعدة البيانات
            self._init_database()

            # كتابة إعدادات التطبيق
            self._write_config()

            return True

        except Exception as e:
            self._log_error(f"Error initializing system: {e}")
            return False

    def _init_database(self):
        """تهيئة قاعدة البيانات"""
        conn = sqlite3.connect(self.DATABASE_FILE)
        cursor = conn.cursor()

        # جدول الاشتراكات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT UNIQUE,
                customer_id TEXT,
                start_date TEXT,
                expiry_date TEXT,
                status TEXT CHECK(status IN ('active', 'expired', 'suspended', 'pending')),
                plan_type TEXT,
                max_devices INTEGER DEFAULT 1,
                devices_registered INTEGER DEFAULT 0,
                last_sync TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # جدول الأجهزة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE,
                machine_id TEXT UNIQUE,
                device_name TEXT,
                last_active TEXT,
                is_active INTEGER DEFAULT 1,
                subscription_id INTEGER,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
            )
        ''')

        # جدول الاستخدام
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                action_type TEXT,
                details TEXT,
                device_id TEXT,
                subscription_id INTEGER,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
            )
        ''')

        # جدول الأخطاء
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                error_code TEXT,
                error_message TEXT,
                device_id TEXT,
                resolved INTEGER DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

    def _write_config(self):
        """كتابة إعدادات التطبيق"""
        config = {
            'app_id': self.APP_ID,
            'app_version': self.APP_VERSION,
            'machine_id': self.machine_id,
            'installation_date': datetime.now().isoformat(),
            'last_update_check': None,
            'update_available': False,
            'auto_update': True
        }

        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)

    def check_subscription(self) -> Dict[str, Any]:
        """التحقق من حالة الاشتراك"""
        try:
            # 1. التحقق المحلي أولاً
            local_status = self._check_local_subscription()

            # 2. إذا كانت الرخصة غير سارية، الاتصال بالسيرفر
            if not local_status['valid'] or local_status.get('needs_sync', False):
                server_status = self._check_server_subscription()

                if server_status['valid']:
                    # تحديث البيانات المحلية
                    self._update_local_subscription(server_status)
                    return server_status
                else:
                    # إذا فشل الاتصال بالسيرفر، التحقق من المدة المسموحة للعمل دون اتصال
                    if local_status['valid']:
                        offline_days = self._get_offline_days(local_status.get('last_sync'))
                        if offline_days <= self.MAX_OFFLINE_DAYS:
                            return local_status

            return local_status

        except Exception as e:
            self._log_error(f"Subscription check error: {e}")
            return {
                'valid': False,
                'message': 'خطأ في النظام، الرجاء الاتصال بالدعم',
                'error_code': 'SYSTEM_ERROR'
            }

    def _check_local_subscription(self) -> Dict[str, Any]:
        """التحقق من الاشتراك المحلي"""
        try:
            conn = sqlite3.connect(self.DATABASE_FILE)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT s.license_key, s.expiry_date, s.status, s.last_sync, s.plan_type,
                       d.device_id, d.last_active
                FROM subscriptions s
                LEFT JOIN devices d ON s.id = d.subscription_id AND d.machine_id = ?
                WHERE s.status = 'active'
                ORDER BY s.expiry_date DESC
                LIMIT 1
            ''', (self.machine_id,))

            result = cursor.fetchone()
            conn.close()

            if not result:
                return {
                    'valid': False,
                    'message': 'لا يوجد اشتراك نشط على هذا الجهاز',
                    'needs_sync': True
                }

            license_key, expiry_date_str, status, last_sync, plan_type, device_id, last_active = result

            # التحقق من تاريخ الانتهاء
            expiry_date = datetime.fromisoformat(expiry_date_str)
            today = datetime.now()

            if expiry_date < today:
                return {
                    'valid': False,
                    'message': 'انتهت فترة الاشتراك',
                    'expiry_date': expiry_date_str,
                    'needs_sync': True
                }

            # التحقق من آخر مزامنة
            needs_sync = False
            if last_sync:
                last_sync_date = datetime.fromisoformat(last_sync)
                if (today - last_sync_date).days > 1:
                    needs_sync = True

            remaining_days = (expiry_date - today).days

            return {
                'valid': True,
                'message': f'الاشتراك ساري - {plan_type}',
                'expiry_date': expiry_date_str,
                'remaining_days': remaining_days,
                'plan_type': plan_type,
                'license_key': license_key,
                'device_id': device_id,
                'last_sync': last_sync,
                'needs_sync': needs_sync
            }

        except Exception as e:
            self._log_error(f"Local subscription check error: {e}")
            return {'valid': False, 'message': 'خطأ في قاعدة البيانات المحلية'}

    def _check_server_subscription(self) -> Dict[str, Any]:
        """الاتصال بالسيرفر للتحقق من الاشتراك"""
        try:
            headers = {
                'Authorization': f'Bearer {self.API_KEY}',
                'Content-Type': 'application/json',
                'X-Device-ID': self.machine_id,
                'X-App-Version': self.APP_VERSION
            }

            payload = {
                'action': 'validate_subscription',
                'machine_id': self.machine_id,
                'timestamp': datetime.now().isoformat(),
                'app_id': self.APP_ID
            }

            response = requests.post(
                f"{self.API_URL}/subscription/validate",
                json=payload,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    subscription_data = data.get('data', {})

                    # حفظ توكن الجلسة
                    self.session_token = data.get('session_token')

                    return {
                        'valid': True,
                        'message': data.get('message', 'الاشتراك ساري'),
                        'expiry_date': subscription_data.get('expiry_date'),
                        'remaining_days': subscription_data.get('remaining_days', 0),
                        'plan_type': subscription_data.get('plan_type', 'basic'),
                        'license_key': subscription_data.get('license_key'),
                        'customer_id': subscription_data.get('customer_id'),
                        'max_devices': subscription_data.get('max_devices', 1),
                        'devices_registered': subscription_data.get('devices_registered', 0)
                    }
                else:
                    return {
                        'valid': False,
                        'message': data.get('message', 'الاشتراك غير صالح'),
                        'error_code': data.get('error_code', 'INVALID_SUBSCRIPTION')
                    }
            else:
                return {
                    'valid': False,
                    'message': f'خطأ في الاتصال بالسيرفر: {response.status_code}',
                    'error_code': 'SERVER_ERROR'
                }

        except requests.exceptions.Timeout:
            return {
                'valid': False,
                'message': 'انتهت مدة الاتصال بالسيرفر',
                'error_code': 'TIMEOUT'
            }
        except requests.exceptions.ConnectionError:
            return {
                'valid': False,
                'message': 'لا يمكن الاتصال بالسيرفر',
                'error_code': 'CONNECTION_ERROR'
            }
        except Exception as e:
            self._log_error(f"Server subscription check error: {e}")
            return {
                'valid': False,
                'message': 'خطأ غير متوقع في الاتصال',
                'error_code': 'UNKNOWN_ERROR'
            }

    def activate_license(self, license_key: str) -> Tuple[bool, str]:
        """تفعيل مفتاح الترخيص"""
        try:
            headers = {
                'Authorization': f'Bearer {self.API_KEY}',
                'Content-Type': 'application/json',
                'X-Device-ID': self.machine_id
            }

            payload = {
                'action': 'activate_license',
                'license_key': license_key,
                'machine_id': self.machine_id,
                'device_name': platform.node(),
                'timestamp': datetime.now().isoformat(),
                'app_id': self.APP_ID,
                'app_version': self.APP_VERSION
            }

            response = requests.post(
                f"{self.API_URL}/subscription/activate",
                json=payload,
                headers=headers,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    subscription_data = data.get('data', {})

                    # حفظ البيانات محلياً
                    self._save_subscription_data(subscription_data)

                    # حفظ توكن الجلسة
                    self.session_token = data.get('session_token')

                    # تسجيل النجاح
                    self._log_action('LICENSE_ACTIVATED', f'License: {license_key[:10]}...')

                    return True, data.get('message', 'تم التفعيل بنجاح')
                else:
                    error_msg = data.get('message', 'فشل التفعيل')
                    error_code = data.get('error_code', 'ACTIVATION_FAILED')

                    # تسجيل الخطأ
                    self._log_error(f"License activation failed: {error_msg}", error_code)

                    return False, error_msg
            else:
                error_msg = f'خطأ في السيرفر: {response.status_code}'
                self._log_error(f"Server error during activation: {error_msg}")
                return False, error_msg

        except requests.exceptions.Timeout:
            error_msg = 'انتهت مدة الاتصال بالسيرفر'
            self._log_error(f"Activation timeout: {error_msg}", 'ACTIVATION_TIMEOUT')
            return False, error_msg
        except requests.exceptions.ConnectionError:
            error_msg = 'لا يمكن الاتصال بالسيرفر'
            self._log_error(f"Activation connection error: {error_msg}", 'CONNECTION_ERROR')
            return False, error_msg
        except Exception as e:
            error_msg = f'خطأ غير متوقع: {str(e)}'
            self._log_error(f"Unexpected activation error: {error_msg}", 'UNKNOWN_ERROR')
            return False, error_msg

    def _save_subscription_data(self, data: Dict[str, Any]):
        """حفظ بيانات الاشتراك محلياً"""
        try:
            conn = sqlite3.connect(self.DATABASE_FILE)
            cursor = conn.cursor()

            # إدخال أو تحديث بيانات الاشتراك
            cursor.execute('''
                INSERT OR REPLACE INTO subscriptions 
                (license_key, customer_id, start_date, expiry_date, status, plan_type, 
                 max_devices, devices_registered, last_sync)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('license_key'),
                data.get('customer_id'),
                data.get('start_date'),
                data.get('expiry_date'),
                'active',
                data.get('plan_type', 'basic'),
                data.get('max_devices', 1),
                data.get('devices_registered', 0),
                datetime.now().isoformat()
            ))

            # الحصول على معرف الاشتراك
            subscription_id = cursor.lastrowid

            # إدخال أو تحديث بيانات الجهاز
            cursor.execute('''
                INSERT OR REPLACE INTO devices 
                (device_id, machine_id, device_name, last_active, is_active, subscription_id)
                VALUES (?, ?, ?, ?, 1, ?)
            ''', (
                data.get('device_id', self.machine_id),
                self.machine_id,
                platform.node(),
                datetime.now().isoformat(),
                subscription_id
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            self._log_error(f"Error saving subscription data: {e}")

    def _update_local_subscription(self, server_data: Dict[str, Any]):
        """تحديث البيانات المحلية من السيرفر"""
        try:
            conn = sqlite3.connect(self.DATABASE_FILE)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE subscriptions 
                SET expiry_date = ?, status = 'active', last_sync = ?
                WHERE license_key = ?
            ''', (
                server_data.get('expiry_date'),
                datetime.now().isoformat(),
                server_data.get('license_key')
            ))

            cursor.execute('''
                UPDATE devices 
                SET last_active = ?
                WHERE machine_id = ?
            ''', (datetime.now().isoformat(), self.machine_id))

            conn.commit()
            conn.close()

        except Exception as e:
            self._log_error(f"Error updating local subscription: {e}")

    def _get_offline_days(self, last_sync: str) -> int:
        """الحصول على عدد الأيام منذ آخر مزامنة"""
        if not last_sync:
            return self.MAX_OFFLINE_DAYS + 1

        try:
            last_sync_date = datetime.fromisoformat(last_sync)
            days_offline = (datetime.now() - last_sync_date).days
            return days_offline
        except:
            return self.MAX_OFFLINE_DAYS + 1

    def log_usage(self, action_type: str, details: str = ""):
        """تسجيل استخدام التطبيق"""
        try:
            conn = sqlite3.connect(self.DATABASE_FILE)
            cursor = conn.cursor()

            # الحصول على معرف الاشتراك
            cursor.execute('SELECT id FROM subscriptions WHERE status = "active" LIMIT 1')
            result = cursor.fetchone()
            subscription_id = result[0] if result else None

            cursor.execute('''
                INSERT INTO usage_logs 
                (date, action_type, details, device_id, subscription_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                action_type,
                details,
                self.machine_id,
                subscription_id
            ))

            conn.commit()
            conn.close()

            # إرسال إلى السيرفر إذا كان هناك اتصال
            if self.session_token and subscription_id:
                self._send_usage_to_server(action_type, details)

        except Exception as e:
            self._log_error(f"Error logging usage: {e}")

    def _send_usage_to_server(self, action_type: str, details: str):
        """إرسال بيانات الاستخدام إلى السيرفر"""
        try:
            headers = {
                'Authorization': f'Bearer {self.session_token}',
                'Content-Type': 'application/json',
                'X-Device-ID': self.machine_id
            }

            payload = {
                'action': 'log_usage',
                'action_type': action_type,
                'details': details,
                'timestamp': datetime.now().isoformat(),
                'device_id': self.machine_id
            }

            requests.post(
                f"{self.API_URL}/usage/log",
                json=payload,
                headers=headers,
                timeout=5
            )

        except:
            pass  # تجاهل الأخطاء في إرسال الاستخدام

    def _log_error(self, error_message: str, error_code: str = None):
        """تسجيل الأخطاء"""
        try:
            conn = sqlite3.connect(self.DATABASE_FILE)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO error_logs 
                (timestamp, error_code, error_message, device_id)
                VALUES (?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                error_code or 'UNKNOWN',
                error_message,
                self.machine_id
            ))

            conn.commit()
            conn.close()

        except:
            pass  # لا نريد أن يفشل التطبيق بسبب تسجيل الأخطاء

    def _log_action(self, action_type: str, details: str = ""):
        """تسجيل الإجراءات"""
        self.log_usage(action_type, details)

    def sync_with_server(self) -> bool:
        """مزامنة البيانات مع السيرفر"""
        try:
            status = self._check_server_subscription()
            if status['valid']:
                self._update_local_subscription(status)
                return True
            return False
        except:
            return False

    def get_usage_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الاستخدام"""
        try:
            conn = sqlite3.connect(self.DATABASE_FILE)
            cursor = conn.cursor()

            # إحصائيات اليوم
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) FROM usage_logs 
                WHERE DATE(date) = DATE(?) AND action_type = 'MESSAGE_SENT'
            ''', (today,))
            messages_today = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM usage_logs 
                WHERE DATE(date) = DATE(?) AND action_type = 'IMAGE_SENT'
            ''', (today,))
            images_today = cursor.fetchone()[0]

            # إحصائيات الشهر
            month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) FROM usage_logs 
                WHERE DATE(date) >= DATE(?) AND action_type = 'MESSAGE_SENT'
            ''', (month_start,))
            messages_month = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM usage_logs 
                WHERE DATE(date) >= DATE(?) AND action_type = 'IMAGE_SENT'
            ''', (month_start,))
            images_month = cursor.fetchone()[0]

            conn.close()

            return {
                'today': {
                    'messages': messages_today,
                    'images': images_today
                },
                'this_month': {
                    'messages': messages_month,
                    'images': images_month
                }
            }

        except Exception as e:
            self._log_error(f"Error getting usage stats: {e}")
            return {'today': {'messages': 0, 'images': 0}, 'this_month': {'messages': 0, 'images': 0}}


# ================================================
# واجهة تفعيل البرنامج
# ================================================

class ActivationWindow:
    """نافذة تفعيل البرنامج"""

    def __init__(self, subscription_manager: SecureSubscriptionManager):
        self.subscription = subscription_manager
        self.window = None
        self.activation_successful = False

    def show(self) -> bool:
        """عرض نافذة التفعيل"""
        self.window = tk.Tk()
        self.window.title("⚡ تفعيل البرنامج - نظام الاشتراكات")
        self.window.geometry("600x500")
        self.window.configure(bg="#2c3e50")
        self.window.resizable(False, False)

        # مركزة النافذة
        self._center_window()

        # جعل النافذة حصرية
        self.window.attributes('-topmost', True)
        self.window.grab_set()

        # منع إغلاق النافذة
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        # إنشاء الواجهة
        self._create_ui()

        # تشغيل النافذة
        self.window.mainloop()

        return self.activation_successful

    def _center_window(self):
        """توسيط النافذة"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def _create_ui(self):
        """إنشاء واجهة المستخدم"""
        # إطار العنوان
        title_frame = tk.Frame(self.window, bg="#3498db", height=80)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        tk.Label(title_frame, text="🔐 تفعيل البرنامج",
                 font=('Cairo', 20, 'bold'),
                 bg="#3498db", fg="white").pack(expand=True)

        tk.Label(title_frame, text="نظام الاشتراكات الشهرية",
                 font=('Cairo', 12),
                 bg="#3498db", fg="#ecf0f1").pack()

        # إطار المحتوى
        content_frame = tk.Frame(self.window, bg="#2c3e50", padx=30, pady=20)
        content_frame.pack(fill="both", expand=True)

        # معلومات الجهاز
        device_frame = tk.LabelFrame(content_frame, text="💻 معلومات الجهاز",
                                     font=('Cairo', 11, 'bold'),
                                     bg="#34495e", fg="#ecf0f1", padx=15, pady=10)
        device_frame.pack(fill="x", pady=(0, 20))

        tk.Label(device_frame, text=f"معرف الجهاز: {self.subscription.machine_id}",
                 font=('Cairo', 10), bg="#34495e", fg="#bdc3c7",
                 anchor="w").pack(fill="x", pady=2)

        tk.Label(device_frame, text=f"اسم الجهاز: {platform.node()}",
                 font=('Cairo', 10), bg="#34495e", fg="#bdc3c7",
                 anchor="w").pack(fill="x", pady=2)

        tk.Label(device_frame, text=f"نظام التشغيل: {platform.system()} {platform.release()}",
                 font=('Cairo', 10), bg="#34495e", fg="#bdc3c7",
                 anchor="w").pack(fill="x", pady=2)

        # إطار إدخال مفتاح الترخيص
        key_frame = tk.LabelFrame(content_frame, text="🔑 مفتاح الترخيص",
                                  font=('Cairo', 11, 'bold'),
                                  bg="#34495e", fg="#ecf0f1", padx=15, pady=15)
        key_frame.pack(fill="x", pady=(0, 20))

        tk.Label(key_frame, text="أدخل مفتاح الترخيص الذي حصلت عليه:",
                 font=('Cairo', 10), bg="#34495e", fg="#ecf0f1",
                 anchor="w").pack(fill="x", pady=(0, 10))

        # حقل إدخال مفتاح الترخيص
        self.license_entry = tk.Entry(key_frame, font=('Cairo', 12),
                                      width=40, bd=2, relief="solid",
                                      justify="center")
        self.license_entry.pack(pady=(0, 10))
        self.license_entry.focus_set()

        # زر التفعيل
        self.activate_button = tk.Button(key_frame, text="تفعيل",
                                         command=self._activate_license,
                                         bg="#27ae60", fg="white",
                                         font=('Cairo', 12, 'bold'),
                                         width=15, height=1,
                                         cursor="hand2")
        self.activate_button.pack(pady=5)

        # رسالة الحالة
        self.status_label = tk.Label(key_frame, text="",
                                     font=('Cairo', 10),
                                     bg="#34495e", fg="#e74c3c",
                                     wraplength=400, justify="center")
        self.status_label.pack(pady=5)

        # معلومات الاتصال
        contact_frame = tk.LabelFrame(content_frame, text="📞 الدعم الفني",
                                      font=('Cairo', 11, 'bold'),
                                      bg="#34495e", fg="#ecf0f1", padx=15, pady=10)
        contact_frame.pack(fill="x", pady=(0, 10))

        contact_text = """
        للحصول على مفتاح ترخيص أو تجديد الاشتراك:

        📱 الهاتف: 771831482 967+
        ✉️ البريد: support@whatsapp-sender.com
        ⏰ ساعات العمل: 9:00 ص - 5:00 م

        ⚠️ بدون تفعيل، البرنامج سيتوقف عن العمل
        """

        tk.Label(contact_frame, text=contact_text,
                 font=('Cairo', 9),
                 bg="#34495e", fg="#bdc3c7",
                 justify="left", anchor="w").pack(fill="x")

        # زر الخروج
        exit_button = tk.Button(content_frame, text="🚫 إغلاق البرنامج",
                                command=self._exit_app,
                                bg="#e74c3c", fg="white",
                                font=('Cairo', 11),
                                width=20, height=1,
                                cursor="hand2")
        exit_button.pack(pady=10)

        # ربط زر Enter بالتفعيل
        self.window.bind('<Return>', lambda e: self._activate_license())

    def _activate_license(self):
        """تفعيل الرخصة"""
        license_key = self.license_entry.get().strip()

        if not license_key:
            self.status_label.config(text="❌ الرجاء إدخال مفتاح الترخيص", fg="#e74c3c")
            return

        # تعطيل الزر أثناء المعالجة
        self.activate_button.config(state="disabled", text="جاري التفعيل...")
        self.status_label.config(text="جاري التحقق من الترخيص...", fg="#f39c12")
        self.window.update()

        # محاولة التفعيل
        success, message = self.subscription.activate_license(license_key)

        if success:
            self.status_label.config(text=f"✅ {message}", fg="#27ae60")
            self.activation_successful = True

            # الانتظار ثم إغلاق النافذة
            self.window.after(2000, self._close_window)
        else:
            self.status_label.config(text=f"❌ {message}", fg="#e74c3c")
            self.activate_button.config(state="normal", text="تفعيل")

    def _close_window(self):
        """إغلاق النافذة"""
        if self.window:
            self.window.destroy()

    def _on_close(self):
        """عند محاولة إغلاق النافذة"""
        if not self.activation_successful:
            response = messagebox.askyesno("تأكيد",
                                           "❌ التفعيل مطلوب لاستخدام البرنامج\n\n"
                                           "هل تريد إغلاق البرنامج؟")
            if response:
                self._exit_app()

    def _exit_app(self):
        """إغلاق التطبيق"""
        self.window.destroy()
        sys.exit(0)


# ================================================
# الفئة الرئيسية للتطبيق
# ================================================

class WhatsAppSenderPro:
    """التطبيق الرئيسي لإرسال واتساب"""

    def __init__(self):
        # تهيئة نظام الاشتراكات
        self.subscription = SecureSubscriptionManager()

        # التحقق من التهيئة
        if not self.subscription.initialize_system():
            messagebox.showerror("خطأ", "فشل في تهيئة النظام!")
            sys.exit(1)

        # التحقق من الاشتراك
        self._check_subscription_on_start()

        # إعدادات التطبيق
        self.root = None
        self.is_running = False
        self.is_paused = False
        self.should_stop = False

        # إعدادات الإرسال
        self.send_mode = "images"  # images, messages_only
        self.images_folder = ""
        self.names_file = ""
        self.phone_numbers_file = ""
        self.country_code = "+966"
        self.message_box_coords = None

        # إعدادات الرسائل
        self.messages = ["مرحباً، هذه رسالة تجريبية"]
        self.second_messages = ["شكراً لك"]
        self.second_messages_count = 1
        self.add_student_name = True

        # إعدادات التوقيت
        self.delay_between_messages = 5
        self.restart_after = 50
        self.slow_mode = False
        self.slow_mode_delay = 10

        # العدادات
        self.sent_count = 0
        self.failed_count = 0
        self.current_file = ""

        # التقارير
        self.report_data = []
        self.start_time = None

        # إعدادات الواجهة
        self.dark_mode = True
        self.current_language = "ar"

        # تحميل الإعدادات
        self._load_settings()

        # إنشاء واجهة المستخدم
        self._create_gui()

        # بدء فحص الاشتراك الدوري
        self._start_subscription_check()

    def _check_subscription_on_start(self):
        """التحقق من الاشتراك عند بدء التشغيل"""
        status = self.subscription.check_subscription()

        if not status['valid']:
            # عرض نافذة التفعيل
            activation_window = ActivationWindow(self.subscription)
            activated = activation_window.show()

            if not activated:
                # إذا لم يتم التفعيل، إغلاق التطبيق
                sys.exit(0)

            # التحقق مرة أخرى بعد التفعيل
            status = self.subscription.check_subscription()
            if not status['valid']:
                messagebox.showerror("خطأ", "فشل التفعيل! الرجاء المحاولة مرة أخرى.")
                sys.exit(0)

    def _load_settings(self):
        """تحميل الإعدادات"""
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                # تطبيق الإعدادات
                for key, value in settings.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
        except:
            pass

    def _save_settings(self):
        """حفظ الإعدادات"""
        try:
            settings = {
                'images_folder': self.images_folder,
                'names_file': self.names_file,
                'phone_numbers_file': self.phone_numbers_file,
                'country_code': self.country_code,
                'messages': self.messages,
                'second_messages': self.second_messages,
                'second_messages_count': self.second_messages_count,
                'add_student_name': self.add_student_name,
                'message_box_coords': self.message_box_coords,
                'delay_between_messages': self.delay_between_messages,
                'restart_after': self.restart_after,
                'slow_mode': self.slow_mode,
                'slow_mode_delay': self.slow_mode_delay,
                'send_mode': self.send_mode,
                'dark_mode': self.dark_mode
            }

            with open("settings.json", 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"Error saving settings: {e}")

    def _create_gui(self):
        """إنشاء واجهة المستخدم"""
        self.root = tk.Tk()
        self.root.title("📱 مرسل واتساب الاحترافي - نظام الاشتراكات")
        self.root.geometry("1100x700")
        self.root.minsize(1000, 650)

        # مركزة النافذة
        self._center_window()

        # إعداد الأيقونة
        self._set_icon()

        # إنشاء الواجهة
        self._setup_ui()

        # ربط حدث إغلاق النافذة
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # بدء التحديث التلقائي
        self._start_auto_updates()

    def _center_window(self):
        """توسيط النافذة"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _set_icon(self):
        """تعيين أيقونة التطبيق"""
        try:
            # محاولة تحميل أيقونة من ملف
            if os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except:
            pass

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        # إنشاء شريط القوائم
        self._create_menu_bar()

        # إنشاء الإطار الرئيسي
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # إنشاء نظام التبويب
        self.tab_control = ttk.Notebook(main_frame)

        # تبويب الإرسال الرئيسي
        self.main_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.main_tab, text="📤 الإرسال الرئيسي")

        # تبويب الإعدادات
        self.settings_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.settings_tab, text="⚙️ الإعدادات")

        # تبويب التقارير
        self.reports_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.reports_tab, text="📊 التقارير")

        # تبويب الاشتراك
        self.subscription_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.subscription_tab, text="⭐ الاشتراك")

        self.tab_control.pack(fill="both", expand=True)

        # إنشاء محتوى التبويبات
        self._create_main_tab()
        self._create_settings_tab()
        self._create_reports_tab()
        self._create_subscription_tab()

        # إنشاء شريط الحالة
        self._create_status_bar()

    def _create_menu_bar(self):
        """إنشاء شريط القوائم"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # قائمة ملف
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ملف", menu=file_menu)
        file_menu.add_command(label="حفظ الإعدادات", command=self._save_settings)
        file_menu.add_separator()
        file_menu.add_command(label="خروج", command=self._on_closing)

        # قائمة عرض
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="عرض", menu=view_menu)
        view_menu.add_command(label="ملء الشاشة", command=self._toggle_fullscreen)
        view_menu.add_command(label="تبديل الثيم", command=self._toggle_theme)

        # قائمة مساعدة
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="مساعدة", menu=help_menu)
        help_menu.add_command(label="دليل الاستخدام", command=self._show_help)
        help_menu.add_command(label="حول البرنامج", command=self._show_about)

    def _create_main_tab(self):
        """إنشاء تبويب الإرسال الرئيسي"""
        # إطار قابل للتمرير
        canvas = tk.Canvas(self.main_tab)
        scrollbar = ttk.Scrollbar(self.main_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # نوع الإرسال
        mode_frame = ttk.LabelFrame(scrollable_frame, text="🔄 نوع الإرسال", padding=10)
        mode_frame.pack(fill="x", pady=(0, 10))

        self.mode_var = tk.StringVar(value=self.send_mode)

        ttk.Radiobutton(mode_frame, text="إرسال صور مع رسائل",
                        variable=self.mode_var, value="images",
                        command=self._on_mode_change).pack(anchor="w", pady=2)

        ttk.Radiobutton(mode_frame, text="إرسال رسائل فقط",
                        variable=self.mode_var, value="messages_only",
                        command=self._on_mode_change).pack(anchor="w", pady=2)

        # الملفات
        files_frame = ttk.LabelFrame(scrollable_frame, text="📁 الملفات", padding=10)
        files_frame.pack(fill="x", pady=(0, 10))

        # مجلد الصور
        self.images_frame = ttk.Frame(files_frame)
        self.images_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(self.images_frame, text="مجلد الصور:").pack(side="left", padx=(0, 10))

        self.images_var = tk.StringVar(value=self.images_folder)
        images_entry = ttk.Entry(self.images_frame, textvariable=self.images_var,
                                 state="readonly", width=40)
        images_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ttk.Button(self.images_frame, text="📂 تصفح",
                   command=self._select_images_folder).pack(side="left")

        # ملف الأسماء
        self.names_frame = ttk.Frame(files_frame)
        self.names_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(self.names_frame, text="ملف الأسماء:").pack(side="left", padx=(0, 10))

        self.names_var = tk.StringVar(value=self.names_file)
        names_entry = ttk.Entry(self.names_frame, textvariable=self.names_var,
                                state="readonly", width=40)
        names_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ttk.Button(self.names_frame, text="📄 تصفح",
                   command=self._select_names_file).pack(side="left")

        # ملف الأرقام
        self.numbers_frame = ttk.Frame(files_frame)
        self.numbers_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(self.numbers_frame, text="ملف الأرقام:").pack(side="left", padx=(0, 10))

        self.numbers_var = tk.StringVar(value=self.phone_numbers_file)
        numbers_entry = ttk.Entry(self.numbers_frame, textvariable=self.numbers_var,
                                  state="readonly", width=40)
        numbers_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ttk.Button(self.numbers_frame, text="📱 تصفح",
                   command=self._select_numbers_file).pack(side="left")

        # تحديث العرض
        self._update_files_visibility()

        # إعدادات الرسائل
        msg_frame = ttk.LabelFrame(scrollable_frame, text="💬 الرسائل", padding=10)
        msg_frame.pack(fill="x", pady=(0, 10))

        # مفتاح الدولة
        ttk.Label(msg_frame, text="مفتاح الدولة:").pack(side="left", padx=(0, 10))

        self.country_var = tk.StringVar(value=self.country_code)
        country_entry = ttk.Entry(msg_frame, textvariable=self.country_var, width=15)
        country_entry.pack(side="left", padx=(0, 20))

        ttk.Label(msg_frame, text="مثال: +966 للسعودية").pack(side="left")

        # موقع مربع الرسالة
        coords_frame = ttk.Frame(msg_frame)
        coords_frame.pack(fill="x", pady=10)

        ttk.Label(coords_frame, text="موقع مربع الرسالة:").pack(side="left", padx=(0, 10))

        self.coords_var = tk.StringVar(value=str(self.message_box_coords) if self.message_box_coords else "غير محدد")
        coords_entry = ttk.Entry(coords_frame, textvariable=self.coords_var,
                                 state="readonly", width=20)
        coords_entry.pack(side="left", padx=(0, 10))

        ttk.Button(coords_frame, text="🎯 تحديد",
                   command=self._select_message_box).pack(side="left")

        # إضافة اسم الطالب
        self.add_name_var = tk.BooleanVar(value=self.add_student_name)
        ttk.Checkbutton(msg_frame, text="إضافة اسم الطالب للرسالة",
                        variable=self.add_name_var).pack(anchor="w")

        # إعدادات التوقيت
        time_frame = ttk.LabelFrame(scrollable_frame, text="⏰ التوقيت", padding=10)
        time_frame.pack(fill="x", pady=(0, 10))

        grid_frame = ttk.Frame(time_frame)
        grid_frame.pack(fill="x")

        ttk.Label(grid_frame, text="التأخير بين الرسائل (ثواني):").grid(row=0, column=0, sticky="w", pady=5)

        self.delay_var = tk.StringVar(value=str(self.delay_between_messages))
        ttk.Entry(grid_frame, textvariable=self.delay_var, width=10).grid(row=0, column=1, sticky="w", padx=(0, 20),
                                                                          pady=5)

        ttk.Label(grid_frame, text="إعادة التشغيل بعد:").grid(row=0, column=2, sticky="w", pady=5)

        self.restart_var = tk.StringVar(value=str(self.restart_after))
        ttk.Entry(grid_frame, textvariable=self.restart_var, width=10).grid(row=0, column=3, sticky="w", padx=(0, 10),
                                                                            pady=5)

        ttk.Label(grid_frame, text="رسالة").grid(row=0, column=4, sticky="w", pady=5)

        # أزرار التحكم
        control_frame = ttk.LabelFrame(scrollable_frame, text="🎮 التحكم", padding=10)
        control_frame.pack(fill="x", pady=(0, 10))

        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x", pady=10)

        self.start_btn = ttk.Button(btn_frame, text="🚀 بدء الإرسال",
                                    command=self._start_sending,
                                    style="Accent.TButton")
        self.start_btn.pack(side="left", padx=5)

        self.pause_btn = ttk.Button(btn_frame, text="⏸️ إيقاف مؤقت",
                                    command=self._toggle_pause,
                                    state="disabled")
        self.pause_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="⏹️ إيقاف",
                                   command=self._stop_sending,
                                   state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        # شريط التقدم
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill="x", pady=10)

        ttk.Label(progress_frame, text="تقدم الإرسال:").pack(side="left", padx=(0, 10))

        self.progress = Progressbar(progress_frame, length=300, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # العدادات
        self.sent_var = tk.StringVar(value="✅ تم: 0")
        self.failed_var = tk.StringVar(value="❌ فشل: 0")

        ttk.Label(progress_frame, textvariable=self.sent_var).pack(side="left", padx=5)
        ttk.Label(progress_frame, textvariable=self.failed_var).pack(side="left", padx=5)

    def _create_settings_tab(self):
        """إنشاء تبويب الإعدادات"""
        canvas = tk.Canvas(self.settings_tab)
        scrollbar = ttk.Scrollbar(self.settings_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # الرسائل
        msg_frame = ttk.LabelFrame(scrollable_frame, text="📝 الرسائل", padding=10)
        msg_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(msg_frame, text="رسائل البداية (واحدة في كل سطر):").pack(anchor="w", pady=(0, 5))

        self.messages_text = tk.Text(msg_frame, height=4, font=('Cairo', 10))
        self.messages_text.pack(fill="x", pady=(0, 10))
        self.messages_text.insert("1.0", "\n".join(self.messages))

        ttk.Label(msg_frame, text="رسائل المتابعة (واحدة في كل سطر):").pack(anchor="w", pady=(0, 5))

        self.second_messages_text = tk.Text(msg_frame, height=3, font=('Cairo', 10))
        self.second_messages_text.pack(fill="x", pady=(0, 10))
        self.second_messages_text.insert("1.0", "\n".join(self.second_messages))

        ttk.Label(msg_frame, text="عدد رسائل المتابعة:").pack(side="left", padx=(0, 10))

        self.second_count_var = tk.StringVar(value=str(self.second_messages_count))
        ttk.Entry(msg_frame, textvariable=self.second_count_var, width=5).pack(side="left")

        # إعدادات متقدمة
        adv_frame = ttk.LabelFrame(scrollable_frame, text="⚡ إعدادات متقدمة", padding=10)
        adv_frame.pack(fill="x", pady=(0, 10))

        self.slow_var = tk.BooleanVar(value=self.slow_mode)
        ttk.Checkbutton(adv_frame, text="وضع الإرسال البطيء",
                        variable=self.slow_var).pack(anchor="w", pady=2)

        ttk.Label(adv_frame, text="تأخير الوضع البطيء (ثواني):").pack(side="left", padx=(20, 10))

        self.slow_delay_var = tk.StringVar(value=str(self.slow_mode_delay))
        ttk.Entry(adv_frame, textvariable=self.slow_delay_var, width=5).pack(side="left")

        # زر الحفظ
        ttk.Button(scrollable_frame, text="💾 حفظ الإعدادات",
                   command=self._save_settings_gui).pack(pady=20)

    def _create_reports_tab(self):
        """إنشاء تبويب التقارير"""
        # شريط الأدوات
        toolbar = ttk.Frame(self.reports_tab)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(toolbar, text="🔄 تحديث",
                   command=self._load_reports).pack(side="left", padx=5)

        ttk.Button(toolbar, text="📊 تصدير CSV",
                   command=self._export_csv).pack(side="left", padx=5)

        # جدول التقارير
        columns = ("الوقت", "الهاتف", "الطالب", "الملف", "الحالة")

        self.report_tree = ttk.Treeview(self.reports_tab, columns=columns, show="headings", height=20)

        for col in columns:
            self.report_tree.heading(col, text=col)
            self.report_tree.column(col, width=150)

        scrollbar = ttk.Scrollbar(self.reports_tab, orient="vertical", command=self.report_tree.yview)
        self.report_tree.configure(yscrollcommand=scrollbar.set)

        self.report_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # تحميل التقارير
        self._load_reports()

    def _create_subscription_tab(self):
        """إنشاء تبويب الاشتراك"""
        canvas = tk.Canvas(self.subscription_tab)
        scrollbar = ttk.Scrollbar(self.subscription_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # معلومات الاشتراك
        status = self.subscription.check_subscription()

        info_frame = ttk.LabelFrame(scrollable_frame, text="📊 معلومات الاشتراك", padding=15)
        info_frame.pack(fill="x", pady=(0, 20))

        if status['valid']:
            info_text = f"""
            ✅ الحالة: نشط
            📅 تاريخ الانتهاء: {status.get('expiry_date', 'غير معروف')}
            ⏳ الأيام المتبقية: {status.get('remaining_days', 0)}
            📦 نوع الخطة: {status.get('plan_type', 'أساسية')}
            🔑 مفتاح الترخيص: {status.get('license_key', '')[:15]}...
            💻 معرف الجهاز: {self.subscription.machine_id}
            """
        else:
            info_text = f"""
            ❌ الحالة: غير مفعل
            ⚠️ السبب: {status.get('message', 'غير معروف')}
            💻 معرف الجهاز: {self.subscription.machine_id}
            """

        info_label = ttk.Label(info_frame, text=info_text, justify="left")
        info_label.pack()

        # إحصائيات الاستخدام
        stats = self.subscription.get_usage_statistics()

        stats_frame = ttk.LabelFrame(scrollable_frame, text="📈 إحصائيات الاستخدام", padding=15)
        stats_frame.pack(fill="x", pady=(0, 20))

        stats_text = f"""
        📊 إحصائيات اليوم:
        • الرسائل المرسلة: {stats['today']['messages']}
        • الصور المرسلة: {stats['today']['images']}

        📈 إحصائيات الشهر:
        • الرسائل المرسلة: {stats['this_month']['messages']}
        • الصور المرسلة: {stats['this_month']['images']}
        """

        stats_label = ttk.Label(stats_frame, text=stats_text, justify="left")
        stats_label.pack()

        # أزرار التحكم
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(fill="x", pady=20)

        ttk.Button(btn_frame, text="🔄 تحديث الحالة",
                   command=self._refresh_subscription).pack(side="left", padx=5)

        ttk.Button(btn_frame, text="🔑 تفعيل جديد",
                   command=self._show_activation).pack(side="left", padx=5)

        ttk.Button(btn_frame, text="📞 دعم فني",
                   command=self._show_support).pack(side="left", padx=5)

    def _create_status_bar(self):
        """إنشاء شريط الحالة"""
        status_bar = ttk.Frame(self.root, relief="sunken")
        status_bar.pack(side="bottom", fill="x")

        # حالة الاشتراك
        self.sub_status_var = tk.StringVar(value="🔍 جاري التحقق...")
        ttk.Label(status_bar, textvariable=self.sub_status_var).pack(side="left", padx=10)

        # حالة التطبيق
        self.app_status_var = tk.StringVar(value="✅ جاهز")
        ttk.Label(status_bar, textvariable=self.app_status_var).pack(side="left", padx=20)

        # تحديث حالة الاشتراك
        self._update_subscription_status()

    def _update_files_visibility(self):
        """تحديث ظهور حقول الملفات"""
        if self.mode_var.get() == "images":
            self.images_frame.pack()
            self.names_frame.pack()
        else:
            self.images_frame.pack_forget()
            self.names_frame.pack_forget()

        self.numbers_frame.pack()

    def _on_mode_change(self):
        """عند تغيير نوع الإرسال"""
        self._update_files_visibility()

    # ================================================
    # دوال اختيار الملفات
    # ================================================

    def _select_images_folder(self):
        """اختيار مجلد الصور"""
        folder = filedialog.askdirectory(title="اختر مجلد الصور")
        if folder:
            self.images_folder = folder
            self.images_var.set(folder)

    def _select_names_file(self):
        """اختيار ملف الأسماء"""
        file = filedialog.askopenfilename(
            title="اختر ملف الأسماء",
            filetypes=[("ملفات نصية", "*.txt"), ("جميع الملفات", "*.*")]
        )
        if file:
            self.names_file = file
            self.names_var.set(file)

    def _select_numbers_file(self):
        """اختيار ملف الأرقام"""
        file = filedialog.askopenfilename(
            title="اختر ملف الأرقام",
            filetypes=[("ملفات نصية", "*.txt"), ("جميع الملفات", "*.*")]
        )
        if file:
            self.phone_numbers_file = file
            self.numbers_var.set(file)

    def _select_message_box(self):
        """تحديد موقع مربع الرسالة"""
        messagebox.showinfo("تحديد الموقع",
                            "انقر فوق مربع الرسالة في واتساب ويب خلال 5 ثواني...")
        self.root.after(5000, self._capture_message_box)

    def _capture_message_box(self):
        """التقاط موقع مربع الرسالة"""
        try:
            x, y = pyautogui.position()
            self.message_box_coords = (x, y)
            self.coords_var.set(f"({x}, {y})")
            messagebox.showinfo("نجاح", f"تم تحديد الموقع: ({x}, {y})")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في تحديد الموقع: {str(e)}")

    # ================================================
    # دوال الإرسال
    # ================================================

    def _validate_inputs(self):
        """التحقق من المدخلات"""
        # التحقق من الاشتراك أولاً
        status = self.subscription.check_subscription()
        if not status['valid']:
            messagebox.showerror("خطأ",
                                 f"الاشتراك غير مفعل!\n{status.get('message')}")
            return False

        # التحقق حسب نوع الإرسال
        mode = self.mode_var.get()

        if mode == "images":
            if not self.images_var.get():
                messagebox.showerror("خطأ", "الرجاء اختيار مجلد الصور!")
                return False

            if self.add_name_var.get() and not self.names_var.get():
                messagebox.showerror("خطأ", "الرجاء اختيار ملف الأسماء!")
                return False
        else:
            if not self.numbers_var.get():
                messagebox.showerror("خطأ", "الرجاء اختيار ملف الأرقام!")
                return False

        if not self.message_box_coords:
            messagebox.showerror("خطأ", "الرجاء تحديد موقع مربع الرسالة!")
            return False

        # التحقق من مفتاح الدولة
        country_code = self.country_var.get()
        if not country_code.startswith("+"):
            messagebox.showerror("خطأ", "مفتاح الدولة يجب أن يبدأ بعلامة +")
            return False

        return True

    def _start_sending(self):
        """بدء عملية الإرسال"""
        if not self._validate_inputs():
            return

        # تحديث الإعدادات من الواجهة
        self._update_settings_from_gui()

        # إعداد الواجهة
        self._prepare_ui_for_sending()

        # بدء الإرسال في خيط منفصل
        thread = threading.Thread(target=self._sending_thread, daemon=True)
        thread.start()

    def _update_settings_from_gui(self):
        """تحديث الإعدادات من الواجهة"""
        try:
            self.send_mode = self.mode_var.get()
            self.images_folder = self.images_var.get()
            self.names_file = self.names_var.get()
            self.phone_numbers_file = self.numbers_var.get()
            self.country_code = self.country_var.get()
            self.add_student_name = self.add_name_var.get()
            self.delay_between_messages = int(self.delay_var.get())
            self.restart_after = int(self.restart_var.get())
            self.slow_mode = self.slow_var.get()
            self.slow_mode_delay = int(self.slow_delay_var.get())

            # تحديث الرسائل
            self.messages = self.messages_text.get("1.0", tk.END).strip().split('\n')
            self.second_messages = self.second_messages_text.get("1.0", tk.END).strip().split('\n')
            self.second_messages_count = int(self.second_count_var.get())

        except ValueError as e:
            messagebox.showerror("خطأ", f"قيمة غير صحيحة: {str(e)}")
            raise

    def _prepare_ui_for_sending(self):
        """إعداد الواجهة للإرسال"""
        self.is_running = True
        self.is_paused = False
        self.should_stop = False

        self.sent_count = 0
        self.failed_count = 0

        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.stop_btn.config(state="normal")

        self.sent_var.set("✅ تم: 0")
        self.failed_var.set("❌ فشل: 0")

        self.app_status_var.set("🔄 جاري الإرسال...")

    def _sending_thread(self):
        """خيط الإرسال الرئيسي"""
        try:
            mode = self.mode_var.get()

            if mode == "images":
                self._send_images_mode()
            else:
                self._send_messages_mode()

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("خطأ", f"حدث خطأ: {str(e)}"))
        finally:
            self.root.after(0, self._finish_sending)

    def _send_images_mode(self):
        """إرسال الصور"""
        # الحصول على قائمة الصور
        image_files = self._get_image_files()
        if not image_files:
            return

        # الحصول على الأسماء
        student_names = []
        if self.add_student_name:
            student_names = self._read_names_file(len(image_files))
            if not student_names or len(student_names) != len(image_files):
                messagebox.showerror("خطأ", "عدد الأسماء لا يتطابق مع عدد الصور!")
                return
        else:
            student_names = [""] * len(image_files)

        # إعداد شريط التقدم
        self.root.after(0, lambda: self.progress.configure(maximum=len(image_files)))

        # إرسال الصور
        for i, (image_file, student_name) in enumerate(zip(image_files, student_names)):
            if self.should_stop:
                break

            while self.is_paused and not self.should_stop:
                time.sleep(0.5)

            if self.should_stop:
                break

            # إرسال الصورة
            success = self._send_single_image(image_file, student_name)

            # تحديث الواجهة
            self.root.after(0, self._update_progress, i + 1, success)

            # إعادة التشغيل إذا لزم الأمر
            if (i + 1) % self.restart_after == 0 and (i + 1) < len(image_files):
                self._restart_whatsapp()

            # التأخير
            delay = self.slow_mode_delay if self.slow_mode else self.delay_between_messages
            time.sleep(delay)

    def _send_messages_mode(self):
        """إرسال الرسائل فقط"""
        # قراءة الأرقام
        phone_numbers = self._read_numbers_file()
        if not phone_numbers:
            return

        # إعداد شريط التقدم
        self.root.after(0, lambda: self.progress.configure(maximum=len(phone_numbers)))

        # إرسال الرسائل
        for i, phone_number in enumerate(phone_numbers):
            if self.should_stop:
                break

            while self.is_paused and not self.should_stop:
                time.sleep(0.5)

            if self.should_stop:
                break

            # إرسال الرسالة
            success = self._send_single_message(phone_number)

            # تحديث الواجهة
            self.root.after(0, self._update_progress, i + 1, success)

            # إعادة التشغيل إذا لزم الأمر
            if (i + 1) % self.restart_after == 0 and (i + 1) < len(phone_numbers):
                self._restart_whatsapp()

            # التأخير
            delay = self.slow_mode_delay if self.slow_mode else self.delay_between_messages
            time.sleep(delay)

    def _get_image_files(self):
        """الحصول على قائمة الصور"""
        try:
            if not os.path.exists(self.images_folder):
                messagebox.showerror("خطأ", "مجلد الصور غير موجود!")
                return []

            extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
            files = [f for f in os.listdir(self.images_folder)
                     if f.lower().endswith(extensions)]

            files.sort()  # فرز تصاعدي حسب الاسم

            if not files:
                messagebox.showwarning("تحذير", "لا توجد صور في المجلد!")

            return files

        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في قراءة مجلد الصور: {str(e)}")
            return []

    def _read_names_file(self, required_count):
        """قراءة ملف الأسماء"""
        try:
            if not os.path.exists(self.names_file):
                return []

            with open(self.names_file, 'r', encoding='utf-8') as f:
                names = [line.strip() for line in f if line.strip()]

            if len(names) != required_count:
                messagebox.showwarning("تحذير",
                                       f"عدد الأسماء ({len(names)}) لا يتطابق مع عدد الصور ({required_count})")
                return None

            return names

        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في قراءة ملف الأسماء: {str(e)}")
            return None

    def _read_numbers_file(self):
        """قراءة ملف الأرقام"""
        try:
            if not os.path.exists(self.phone_numbers_file):
                return []

            with open(self.phone_numbers_file, 'r', encoding='utf-8') as f:
                numbers = [line.strip() for line in f if line.strip()]

            if not numbers:
                messagebox.showwarning("تحذير", "لا توجد أرقام في الملف!")

            return numbers

        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في قراءة ملف الأرقام: {str(e)}")
            return []

    def _send_single_image(self, image_file, student_name):
        """إرسال صورة واحدة"""
        try:
            # استخراج رقم الهاتف
            phone_number = os.path.splitext(image_file)[0]
            full_number = self.country_code.lstrip('+') + phone_number

            # فتح واتساب
            webbrowser.open(f"whatsapp://send?phone={full_number}")
            time.sleep(3)

            # إرسال الصورة
            image_path = os.path.join(self.images_folder, image_file)
            success = self._send_image_via_whatsapp(image_path, student_name)

            # تسجيل النتيجة
            if success:
                self.sent_count += 1
                self.subscription.log_usage("IMAGE_SENT", image_file)

                self.report_data.append({
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'phone': full_number,
                    'student': student_name,
                    'file': image_file,
                    'status': 'نجاح'
                })
            else:
                self.failed_count += 1

                self.report_data.append({
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'phone': full_number,
                    'student': student_name,
                    'file': image_file,
                    'status': 'فشل'
                })

            return success

        except Exception as e:
            self.failed_count += 1

            self.report_data.append({
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'phone': 'N/A',
                'student': student_name,
                'file': image_file,
                'status': f'خطأ: {str(e)}'
            })

            return False

    def _send_single_message(self, phone_number):
        """إرسال رسالة واحدة"""
        try:
            full_number = self.country_code.lstrip('+') + phone_number

            webbrowser.open(f"whatsapp://send?phone={full_number}")
            time.sleep(3)

            success = self._send_message_via_whatsapp()

            if success:
                self.sent_count += 1
                self.subscription.log_usage("MESSAGE_SENT", phone_number)

                self.report_data.append({
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'phone': full_number,
                    'student': 'N/A',
                    'file': 'رسالة فقط',
                    'status': 'نجاح'
                })
            else:
                self.failed_count += 1

                self.report_data.append({
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'phone': full_number,
                    'student': 'N/A',
                    'file': 'رسالة فقط',
                    'status': 'فشل'
                })

            return success

        except Exception as e:
            self.failed_count += 1

            self.report_data.append({
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'phone': 'N/A',
                'student': 'N/A',
                'file': 'رسالة فقط',
                'status': f'خطأ: {str(e)}'
            })

            return False

    def _send_image_via_whatsapp(self, image_path, student_name):
        """إرسال صورة عبر واتساب"""
        try:
            x, y = self.message_box_coords

            # النقر على مربع الرسالة
            pyautogui.click(x, y)
            time.sleep(1)

            # فتح مربع المرفقات
            pyautogui.hotkey('ctrl', 'shift', 'b')
            time.sleep(2)

            # إدخال مسار الصورة
            fixed_path = os.path.normpath(image_path)
            pyperclip.copy(fixed_path)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(3)

            # إرسال الصورة
            pyautogui.press('enter')
            time.sleep(3)

            # كتابة الرسالة
            if self.messages:
                message = random.choice(self.messages)
                if student_name:
                    message = f"{message} {student_name}"

                pyperclip.copy(message)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(1)
                pyautogui.press('enter')
                time.sleep(2)

            # رسائل المتابعة
            if self.second_messages and self.second_messages_count > 0:
                count = min(self.second_messages_count, len(self.second_messages))
                for _ in range(count):
                    follow_up = random.choice(self.second_messages)
                    if student_name:
                        follow_up = f"{follow_up} {student_name}"

                    pyperclip.copy(follow_up)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(1)
                    pyautogui.press('enter')
                    time.sleep(2)

            return True

        except Exception as e:
            print(f"Error sending image: {e}")
            return False

    def _send_message_via_whatsapp(self):
        """إرسال رسالة عبر واتساب"""
        try:
            x, y = self.message_box_coords

            pyautogui.click(x, y)
            time.sleep(1)

            if self.messages:
                message = random.choice(self.messages)
                pyperclip.copy(message)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(1)
                pyautogui.press('enter')
                time.sleep(2)

            if self.second_messages and self.second_messages_count > 0:
                count = min(self.second_messages_count, len(self.second_messages))
                for _ in range(count):
                    follow_up = random.choice(self.second_messages)
                    pyperclip.copy(follow_up)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(1)
                    pyautogui.press('enter')
                    time.sleep(2)

            return True

        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def _restart_whatsapp(self):
        """إعادة تشغيل واتساب"""
        try:
            # إغلاق واتساب
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and 'whatsapp' in proc.info['name'].lower():
                    proc.kill()

            time.sleep(3)

            # فتح واتساب
            webbrowser.open("whatsapp://")
            time.sleep(5)

        except Exception as e:
            print(f"Error restarting WhatsApp: {e}")

    def _update_progress(self, value, success):
        """تحديث شريط التقدم"""
        self.progress['value'] = value

        self.sent_var.set(f"✅ تم: {self.sent_count}")
        self.failed_var.set(f"❌ فشل: {self.failed_count}")

    def _toggle_pause(self):
        """تبديل حالة الإيقاف المؤقت"""
        self.is_paused = not self.is_paused

        if self.is_paused:
            self.pause_btn.config(text="▶️ متابعة")
            self.app_status_var.set("⏸️ متوقف مؤقتاً")
        else:
            self.pause_btn.config(text="⏸️ إيقاف مؤقت")
            self.app_status_var.set("🔄 جاري الإرسال...")

    def _stop_sending(self):
        """إيقاف عملية الإرسال"""
        self.should_stop = True
        self.app_status_var.set("🛑 يتم الإيقاف...")

    def _finish_sending(self):
        """إنهاء عملية الإرسال"""
        self.is_running = False

        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.pause_btn.config(text="⏸️ إيقاف مؤقت")

        self.app_status_var.set("✅ اكتمل الإرسال")

        # حفظ التقرير
        self._save_report()

        # عرض ملخص
        total = self.sent_count + self.failed_count
        messagebox.showinfo("اكتمل الإرسال",
                            f"✅ تم الإرسال: {self.sent_count}\n"
                            f"❌ فشل: {self.failed_count}\n"
                            f"📊 الإجمالي: {total}")

    def _save_report(self):
        """حفظ التقرير"""
        if not self.report_data:
            return

        try:
            report_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            with open(report_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['الوقت', 'الهاتف', 'الطالب', 'الملف', 'الحالة'])

                for entry in self.report_data:
                    writer.writerow([
                        entry['time'],
                        entry['phone'],
                        entry['student'],
                        entry['file'],
                        entry['status']
                    ])

            print(f"Report saved: {report_file}")

        except Exception as e:
            print(f"Error saving report: {e}")

    def _load_reports(self):
        """تحميل التقارير"""
        # مسح البيانات الحالية
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)

        # تحميل من ملف CSV
        try:
            csv_files = [f for f in os.listdir() if f.startswith('report_') and f.endswith('.csv')]
            if csv_files:
                latest = max(csv_files, key=os.path.getctime)

                with open(latest, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    next(reader)  # تخطي العناوين

                    for row in reader:
                        if len(row) >= 5:
                            self.report_tree.insert("", tk.END, values=row)
        except:
            pass

    def _export_csv(self):
        """تصدير إلى CSV"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("ملفات CSV", "*.csv"), ("جميع الملفات", "*.*")]
            )

            if file_path:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['الوقت', 'الهاتف', 'الطالب', 'الملف', 'الحالة'])

                    for item in self.report_tree.get_children():
                        values = self.report_tree.item(item)['values']
                        writer.writerow(values)

                messagebox.showinfo("نجاح", "تم التصدير بنجاح!")

        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في التصدير: {str(e)}")

    # ================================================
    # دوال الاشتراك
    # ================================================

    def _update_subscription_status(self):
        """تحديث حالة الاشتراك"""
        try:
            status = self.subscription.check_subscription()

            if status['valid']:
                days = status.get('remaining_days', 0)
                self.sub_status_var.set(f"✅ اشتراك ساري - {days} يوم متبقي")
            else:
                self.sub_status_var.set(f"❌ {status.get('message', 'غير مفعل')}")

        except Exception as e:
            self.sub_status_var.set("⚠️ خطأ في التحقق")

        # إعادة الجدولة كل دقيقة
        self.root.after(60000, self._update_subscription_status)

    def _refresh_subscription(self):
        """تحديث حالة الاشتراك"""
        self.sub_status_var.set("🔄 جاري التحديث...")
        self.root.update()

        status = self.subscription.check_subscription()

        if status['valid']:
            days = status.get('remaining_days', 0)
            messagebox.showinfo("الحالة", f"✅ الاشتراك ساري المفعول\nالأيام المتبقية: {days}")
        else:
            messagebox.showerror("الحالة", f"❌ {status.get('message', 'غير مفعل')}")

        self._update_subscription_status()

    def _show_activation(self):
        """عرض نافذة التفعيل"""
        activation_window = ActivationWindow(self.subscription)
        activated = activation_window.show()

        if activated:
            self._update_subscription_status()
            messagebox.showinfo("نجاح", "تم التفعيل بنجاح!")

    def _show_support(self):
        """عرض معلومات الدعم"""
        support_text = """
        📞 الدعم الفني

        للاستفسارات والمشاكل:

        📱 الهاتف: 771831482 967+
        ✉️ البريد: support@whatsapp-sender.com
        🕒 ساعات العمل: 9:00 ص - 5:00 م

        خدماتنا:
        1. تفعيل البرنامج وتجديد الاشتراكات
        2. حل المشاكل الفنية
        3. استقبال المقترحات
        4. تدريب على الاستخدام

        شكراً لثقتك بنا! 🤝
        """

        messagebox.showinfo("الدعم الفني", support_text)

    def _start_subscription_check(self):
        """بدء فحص الاشتراك الدوري"""

        def check():
            try:
                status = self.subscription.check_subscription()
                if not status['valid']:
                    self.root.after(0, self._show_subscription_expired)
            except:
                pass

            # إعادة الجدولة كل ساعة
            self.root.after(3600000, check)

        check()

    def _show_subscription_expired(self):
        """عند انتهاء الاشتراك"""
        response = messagebox.askyesno("انتهاء الاشتراك",
                                       "⏰ انتهت فترة الاشتراك!\n\n"
                                       "يجب تجديد الاشتراك لمواصلة الاستخدام.\n"
                                       "هل تريد التوجه إلى نافذة التفعيل؟")

        if response:
            self._show_activation()
        else:
            # إغلاق التطبيق بعد فترة
            self.root.after(30000, self._force_close)

    def _force_close(self):
        """إجبار التطبيق على الإغلاق"""
        messagebox.showwarning("إغلاق", "سيتم إغلاق التطبيق بسبب انتهاء الاشتراك.")
        self._on_closing()

    # ================================================
    # دوال المساعدة
    # ================================================

    def _save_settings_gui(self):
        """حفظ الإعدادات من الواجهة"""
        try:
            self._update_settings_from_gui()
            self._save_settings()
            messagebox.showinfo("نجاح", "تم حفظ الإعدادات بنجاح!")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في حفظ الإعدادات: {str(e)}")

    def _toggle_fullscreen(self):
        """تبديل وضع ملء الشاشة"""
        self.root.attributes('-fullscreen', not self.root.attributes('-fullscreen'))

    def _toggle_theme(self):
        """تبديل الثيم"""
        self.dark_mode = not self.dark_mode
        messagebox.showinfo("معلومة", "سيتم تطبيق الثيم عند إعادة تشغيل البرنامج")

    def _show_help(self):
        """عرض المساعدة"""
        help_text = """
        📚 دليل الاستخدام السريع:

        1. ⭐ الاشتراك:
           - البرنامج يعمل بنظام اشتراكات شهرية
           - يجب تفعيل البرنامج قبل الاستخدام
           - للدعم الفني: 771831482 967+

        2. 🔄 أنواع الإرسال:
           - إرسال صور مع رسائل: تحتاج لمجلد الصور وملف الأسماء
           - إرسال رسائل فقط: تحتاج فقط لملف الأرقام

        3. 📁 إعدادات الملفات:
           - مجلد الصور: اختر المجلد الذي يحتوي على صور الطلاب
           - ملف الأسماء: ملف نصي يحتوي على أسماء الطلاب
           - ملف الأرقام: ملف نصي كل رقم في سطر

        4. 💬 الرسائل:
           - مفتاح الدولة: أدخل مفتاح الدولة (مثال: +966)
           - تحديد موقع الرسالة: انقر على زر "تحديد"

        5. ⏰ التوقيت:
           - التأخير بين الرسائل: الوقت بين كل رسالة
           - إعادة التشغيل: عدد الرسائل قبل إعادة تشغيل واتساب

        ⚠️ نصائح مهمة:
        - تأكد من فتح واتساب ويب في المتصفح
        - اختبر الإرسال على رقم تجريبي أولاً
        - احفظ الإعدادات المهمة
        """

        messagebox.showinfo("❓ المساعدة", help_text)

    def _show_about(self):
        """عرض معلومات عن البرنامج"""
        about_text = f"""
        📱 مرسل واتساب الاحترافي

        الإصدار: 5.0
        التاريخ: {datetime.now().strftime('%Y-%m-%d')}

        المميزات:
        ✅ نظام اشتراكات شهري مربوط بالسيرفر
        ✅ إرسال صور مع رسائل مخصصة
        ✅ إرسال رسائل فقط بدون صور
        ✅ دعم ملفات الأرقام (كل رقم في سطر)
        ✅ فرز الصور تصاعدياً حسب الاسم
        ✅ إدخال مفتاح الدولة مخصص
        ✅ تقارير تفصيلية
        ✅ واجهة مستخدم عربية

        المطور: م/ يوسف محمد زهير
        الدعم الفني: 771831482 967+

        ⚠️ تحذير:
        هذا البرنامج للأغراض المشروعة فقط

        © 2024 جميع الحقوق محفوظة
        """

        messagebox.showinfo("ℹ️ حول البرنامج", about_text)

    def _start_auto_updates(self):
        """بدء التحديثات التلقائية"""

        def check_updates():
            try:
                # هنا يمكن إضافة كود التحقق من التحديثات
                pass
            except:
                pass

            # إعادة الجدولة كل 24 ساعة
            self.root.after(86400000, check_updates)

        check_updates()

    def _on_closing(self):
        """عند إغلاق النافذة"""
        # التحقق من الاشتراك قبل الإغلاق
        status = self.subscription.check_subscription()

        if not status['valid']:
            response = messagebox.askyesno("تأكيد",
                                           "❌ الاشتراك غير مفعل!\n\n"
                                           "هل تريد إغلاق البرنامج؟")
            if not response:
                return

        # حفظ الإعدادات
        self._save_settings()

        # تسجيل الخروج
        self.subscription.log_usage("APP_CLOSED")

        # إغلاق التطبيق
        self.root.destroy()
        sys.exit(0)

    def run(self):
        """تشغيل التطبيق"""
        self.root.mainloop()


# ================================================
# نقطة الدخول الرئيسية
# ================================================

def main():
    """الدالة الرئيسية"""
    try:
        # إنشاء وتشغيل التطبيق
        app = WhatsAppSenderPro()
        app.run()

    except Exception as e:
        messagebox.showerror("خطأ فادح", f"فشل في تشغيل البرنامج:\n{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # التحقق من صلاحيات المسؤول (على ويندوز)
    if platform.system() == "Windows":
        try:
            import ctypes

            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, __file__, None, 1
                )
                sys.exit(0)
        except:
            pass

    # تشغيل التطبيق

    main()
