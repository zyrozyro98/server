"""
مدير التراخيص - نظام التفعيل والتحقق
"""

import os
import json
import base64
import hashlib
import uuid
import pickle
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

import requests
from cryptography.fernet import Fernet


class LicenseManager:
    def __init__(self, app_id: str, app_name: str, version: str, developer: str):
        self.app_id = app_id
        self.app_name = app_name
        self.version = version
        self.developer = developer

        # ملفات النظام
        self.license_file = "license.dat"
        self.encryption_key_file = "app.key"

        # معلومات النظام
        self.hwid = self.generate_hwid()
        self.system_info = self.get_system_info()

        # حالة الرخصة
        self.license_data = None
        self.is_valid = False
        self.license_info = {}

        # إعدادات الاتصال بالسيرفر
        self.server_url = "https://server-hxb7.onrender.com"  # تغيير لرابط السيرفر الحقيقي
        self.api_timeout = 10

        # التشفير
        self.cipher = None
        self.setup_encryption()

    # ========================================================================
    # نظام التشفير
    # ========================================================================

    def setup_encryption(self):
        """إعداد نظام التشفير"""
        try:
            # إنشاء أو تحميل مفتاح التشفير
            if not os.path.exists(self.encryption_key_file):
                key = Fernet.generate_key()
                with open(self.encryption_key_file, 'wb') as f:
                    f.write(key)
            else:
                with open(self.encryption_key_file, 'rb') as f:
                    key = f.read()

            self.cipher = Fernet(key)
        except Exception as e:
            print(f"خطأ في إعداد التشفير: {e}")
            self.cipher = None

    def encrypt_data(self, data: Dict) -> str:
        """تشفير البيانات"""
        try:
            if self.cipher:
                data_str = json.dumps(data)
                encrypted = self.cipher.encrypt(data_str.encode())
                return base64.b64encode(encrypted).decode()
        except:
            pass
        return ""

    def decrypt_data(self, encrypted_str: str) -> Optional[Dict]:
        """فك تشفير البيانات"""
        try:
            if self.cipher and encrypted_str:
                encrypted_bytes = base64.b64decode(encrypted_str)
                decrypted = self.cipher.decrypt(encrypted_bytes)
                return json.loads(decrypted.decode())
        except:
            pass
        return None

    # ========================================================================
    # HWID وجمع معلومات النظام
    # ========================================================================

    def generate_hwid(self) -> str:
        """إنشاء معرف فريد للجهاز"""
        try:
            # جمع معلومات متعددة من النظام
            system_info = []

            # 1. معرف المعالج
            try:
                import platform
                system_info.append(platform.processor())
            except:
                pass

            # 2. MAC Address
            try:
                import uuid
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                                for elements in range(0, 8 * 6, 8)][::-1])
                system_info.append(mac)
            except:
                pass

            # 3. اسم الجهاز
            try:
                import socket
                system_info.append(socket.gethostname())
            except:
                pass

            # 4. اسم المستخدم
            try:
                import os
                system_info.append(os.getlogin())
            except:
                pass

            # 5. حجم الذاكرة
            try:
                import psutil
                ram = psutil.virtual_memory().total
                system_info.append(str(ram))
            except:
                pass

            # إنشاء الهاش
            combined = "-".join(filter(None, system_info))
            hwid_hash = hashlib.sha256(combined.encode()).hexdigest()

            return hwid_hash[:32]  # إرجاع 32 حرف فقط

        except Exception as e:
            print(f"خطأ في توليد HWID: {e}")
            # استخدام معرف عشوائي كحل احتياطي
            return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

    def get_system_info(self) -> Dict:
        """جمع معلومات النظام"""
        info = {
            "hwid": self.hwid,
            "app_id": self.app_id,
            "app_name": self.app_name,
            "version": self.version,
            "developer": self.developer,
            "first_seen": datetime.now().isoformat(),
            "last_check": datetime.now().isoformat()
        }

        try:
            import platform
            info.update({
                "os": platform.system(),
                "os_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "username": os.getlogin(),
                "hostname": platform.node()
            })
        except:
            pass

        return info

    # ========================================================================
    # إدارة الرخصة المحلية
    # ========================================================================

    def load_and_validate(self) -> bool:
        """تحميل والتحقق من الرخصة"""
        # أولاً: محاولة تحميل الرخصة المحلية
        if self.load_local_license():
            if self.validate_local():
                return True

        # ثانياً: التحقق من السيرفر
        if self.check_with_server():
            return True

        return False

    def load_local_license(self) -> bool:
        """تحميل الرخصة المحلية"""
        try:
            if os.path.exists(self.license_file):
                with open(self.license_file, 'rb') as f:
                    encrypted_data = f.read()

                # فك التشفير
                license_str = self.cipher.decrypt(encrypted_data).decode()
                self.license_data = json.loads(license_str)

                return True
        except Exception as e:
            print(f"خطأ في تحميل الرخصة المحلية: {e}")
            self.license_data = None

        return False

    def validate_local(self) -> bool:
        """التحقق المحلي من الرخصة"""
        if not self.license_data:
            self.is_valid = False
            return False

        try:
            # التحقق من HWID
            saved_hwid = self.license_data.get('hwid')
            if saved_hwid != self.hwid:
                print("HWID لا يتطابق")
                self.is_valid = False
                return False

            # التحقق من تاريخ الانتهاء
            expiry_str = self.license_data.get('expiry_date')
            if expiry_str:
                expiry_date = datetime.fromisoformat(expiry_str)
                if datetime.now() > expiry_date:
                    print("الرخصة منتهية الصلاحية")
                    self.is_valid = False
                    return False

            # تحقق من نوع الرخصة
            license_type = self.license_data.get('type', 'trial')

            # إذا كانت تجريبية، تحقق من المدة
            if license_type == 'trial':
                start_str = self.license_data.get('activation_date')
                if start_str:
                    start_date = datetime.fromisoformat(start_str)
                    trial_days = self.license_data.get('trial_days', 7)
                    trial_end = start_date + timedelta(days=trial_days)

                    if datetime.now() > trial_end:
                        print("انتهت الفترة التجريبية")
                        self.is_valid = False
                        return False

            self.is_valid = True
            self.update_license_info()
            return True

        except Exception as e:
            print(f"خطأ في التحقق المحلي: {e}")
            self.is_valid = False
            return False

    def update_license_info(self):
        """تحديث معلومات الرخصة"""
        if self.license_data:
            self.license_info = {
                'valid': self.is_valid,
                'type': self.license_data.get('type', 'unknown'),
                'plan': self.license_data.get('plan', 'غير محدد'),
                'expiry_date': self.license_data.get('expiry_date'),
                'activation_date': self.license_data.get('activation_date'),
                'hwid': self.hwid[:10] + '...'
            }

            # حساب الأيام المتبقية
            if self.license_info['expiry_date']:
                expiry = datetime.fromisoformat(self.license_info['expiry_date'])
                days_left = (expiry - datetime.now()).days
                self.license_info['days_left'] = max(days_left, 0)
            else:
                self.license_info['days_left'] = 0

    # ========================================================================
    # الاتصال بالسيرفر
    # ========================================================================

    def check_with_server(self) -> bool:
        """التحقق من السيرفر"""
        try:
            # إذا لم يكن هناك ترخيص محلي، لا يمكن التحقق
            if not self.license_data:
                return False

            # بيانات الطلب
            payload = {
                'action': 'validate',
                'license_key': self.license_data.get('license_key'),
                'hwid': self.hwid,
                'app_id': self.app_id,
                'system_info': self.system_info
            }

            # إرسال الطلب
            response = requests.post(
                f"{self.server_url}/api/license/validate",
                json=payload,
                timeout=self.api_timeout
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # تحديث بيانات الرخصة
                    if 'license_data' in result:
                        self.license_data.update(result['license_data'])
                        self.save_local_license()
                        self.validate_local()

                    return True
                else:
                    print(f"فشل التحقق من السيرفر: {result.get('message')}")

            return False

        except requests.exceptions.RequestException as e:
            print(f"خطأ في الاتصال بالسيرفر: {e}")
            # في حالة فشل الاتصال، نعتمد على الرخصة المحلية
            return self.is_valid
        except Exception as e:
            print(f"خطأ غير متوقع في الاتصال بالسيرفر: {e}")
            return self.is_valid

    def activate_license(self, license_key: str, user_info: Dict = None) -> Tuple[bool, str]:
        """تفعيل الرخصة"""
        try:
            # بيانات التنشيط
            payload = {
                'action': 'activate',
                'license_key': license_key,
                'hwid': self.hwid,
                'app_id': self.app_id,
                'system_info': self.system_info,
                'user_info': user_info or {}
            }

            # إرسال طلب التفعيل
            response = requests.post(
                f"{self.server_url}/api/license/activate",
                json=payload,
                timeout=self.api_timeout
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # حفظ بيانات الرخصة
                    self.license_data = result.get('license_data', {})
                    self.save_local_license()
                    self.validate_local()

                    return True, result.get('message', 'تم التفعيل بنجاح')
                else:
                    return False, result.get('message', 'فشل التفعيل')

            return False, f"خطأ في السيرفر: {response.status_code}"

        except requests.exceptions.RequestException as e:
            return False, f"خطأ في الاتصال: {str(e)}"
        except Exception as e:
            return False, f"خطأ غير متوقع: {str(e)}"

    def save_local_license(self):
        """حفظ الرخصة محلياً"""
        try:
            if self.license_data:
                # تحديث وقت آخر فحص
                self.license_data['last_check'] = datetime.now().isoformat()
                self.license_data['hwid'] = self.hwid

                # تشفير وحفظ
                license_str = json.dumps(self.license_data)
                encrypted = self.cipher.encrypt(license_str.encode())

                with open(self.license_file, 'wb') as f:
                    f.write(encrypted)

                return True
        except Exception as e:
            print(f"خطأ في حفظ الرخصة: {e}")

        return False

    # ========================================================================
    # الوظائف المساعدة
    # ========================================================================

    def get_license_info(self) -> Dict:
        """الحصول على معلومات الرخصة"""
        if not self.license_info:
            self.update_license_info()

        return self.license_info.copy()

    def reset_license(self):
        """إعادة تعيين الرخصة"""
        try:
            if os.path.exists(self.license_file):
                os.remove(self.license_file)

            self.license_data = None
            self.is_valid = False
            self.license_info = {}

            return True
        except:
            return False

    def is_trial_available(self) -> bool:
        """التحقق من إمكانية استخدام النسخة التجريبية"""
        # يمكنك إضافة منطق أكثر تعقيداً هنا
        return True

    def get_trial_license(self) -> Tuple[bool, str]:
        """الحصول على ترخيص تجريبي"""
        try:
            # إنشاء ترخيص تجريبي محلي
            trial_data = {
                'license_key': f"TRIAL_{self.hwid[:8]}",
                'type': 'trial',
                'plan': 'تجريبي',
                'activation_date': datetime.now().isoformat(),
                'expiry_date': (datetime.now() + timedelta(days=7)).isoformat(),
                'trial_days': 7,
                'hwid': self.hwid,
                'features': ['basic_sending', 'limited_messages']
            }

            self.license_data = trial_data
            self.save_local_license()
            self.validate_local()

            return True, "تم تفعيل النسخة التجريبية لمدة 7 أيام"

        except Exception as e:

            return False, f"خطأ في التفعيل التجريبي: {str(e)}"
