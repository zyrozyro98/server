"""
📱 WhatsApp Sender Pro - النسخة الاحترافية
الإصدار: 2.0.0
المطور: يوسف محمد زهير
رقم الدعم: 771831482
"""

import os
import sys
import json
import pickle
import threading
import time
import webbrowser
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pyautogui
import pyperclip
from PIL import Image, ImageTk
import psutil
import requests
from cryptography.fernet import Fernet
import base64
import hashlib
import uuid
import platform
import socket
import subprocess

# استيراد وحدات النظام
from license_manager import LicenseManager
from activation_window import ActivationWindow


# ============================================================================
# الكلاس الرئيسي للبرنامج
# ============================================================================

class WhatsAppSenderPro:
    def __init__(self, root):
        self.root = root
        self.root.title("📱 WhatsApp Sender Pro - النسخة الاحترافية")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # إعدادات التطبيق
        self.app_name = "WhatsApp_Sender_Pro_v2"
        self.version = "2.0.0"
        self.developer = "يوسف محمد زهير"
        self.support_number = "771831482"

        # النظام الجديد - الترخيص
        self.license_manager = None
        self.license_info = None
        self.is_licensed = False

        # تهيئة النظام
        self.initialize_license_system()

        # تحميل الإعدادات
        self.settings_file = "whatsapp_sender_settings.dat"
        self.settings = self.load_settings()

        # إنشاء واجهة المستخدم
        self.setup_ui()

        # التحقق الدوري من الرخصة
        self.setup_license_checker()

        # تحديث حالة الرخصة
        self.update_license_status()

    # ========================================================================
    # نظام الترخيص والتفعيل
    # ========================================================================

    def initialize_license_system(self):
        """تهيئة نظام الترخيص"""
        try:
            self.license_manager = LicenseManager(
                app_id="WhatsApp_Sender_Pro_v2",
                app_name="WhatsApp Sender Pro",
                version=self.version,
                developer=self.developer
            )

            # محاولة تحميل الرخصة
            if not self.license_manager.load_and_validate():
                # إذا فشل، اعرض نافذة التفعيل
                self.show_activation_dialog()
            else:
                self.is_licensed = True
                self.license_info = self.license_manager.get_license_info()

        except Exception as e:
            print(f"خطأ في تهيئة نظام الترخيص: {e}")
            self.is_licensed = False

    def show_activation_dialog(self):
        """عرض نافذة التفعيل"""
        if not hasattr(self, 'activation_shown') or not self.activation_shown:
            self.activation_shown = True

            # تعطيل الواجهة مؤقتاً
            self.disable_interface()

            # عرض نافذة التفعيل
            activation_win = tk.Toplevel(self.root)
            activation_win.title("تفعيل البرنامج")
            activation_win.geometry("600x500")
            activation_win.resizable(False, False)
            activation_win.configure(bg="#2c3e50")
            activation_win.transient(self.root)
            activation_win.grab_set()

            # إنشاء نافذة التفعيل
            ActivationWindow(
                parent=activation_win,
                license_manager=self.license_manager,
                on_activate_callback=self.on_license_activated
            )

            # انتظار إغلاق نافذة التفعيل
            self.root.wait_window(activation_win)

    def on_license_activated(self):
        """عند تفعيل الرخصة بنجاح"""
        self.is_licensed = True
        self.license_info = self.license_manager.get_license_info()
        self.enable_interface()
        self.update_license_status()
        messagebox.showinfo("نجاح", "✅ تم تفعيل البرنامج بنجاح!")

    def setup_license_checker(self):
        """إعداد مدقق الرخصة الدوري"""

        def check_license():
            while True:
                try:
                    if self.license_manager:
                        # التحقق من السيرفر كل ساعة
                        if self.license_manager.check_with_server():
                            self.license_info = self.license_manager.get_license_info()
                            self.update_license_status()

                            # تحذير إذا بقي أقل من 3 أيام
                            if self.license_info['days_left'] <= 3:
                                self.show_license_warning()

                        # التحقق المحلي كل دقيقة
                        if not self.license_manager.validate_local():
                            self.is_licensed = False
                            self.show_activation_dialog()

                except Exception as e:
                    print(f"خطأ في فحص الرخصة: {e}")

                time.sleep(60)  # فحص كل دقيقة

        # تشغيل المدقق في خيط منفصل
        checker_thread = threading.Thread(target=check_license, daemon=True)
        checker_thread.start()

    def update_license_status(self):
        """تحديث حالة الرخصة في الواجهة"""
        if hasattr(self, 'license_status_label'):
            if self.is_licensed and self.license_info:
                status_text = f"✅ {self.license_info.get('plan', 'مفعل')}"
                if self.license_info.get('days_left'):
                    status_text += f" | {self.license_info['days_left']} يوم"
                self.license_status_label.config(text=status_text, fg="#27ae60")
            else:
                self.license_status_label.config(text="❌ غير مفعل", fg="#e74c3c")

    def show_license_warning(self):
        """عرض تحذير انتهاء الرخصة"""
        if self.license_info and self.license_info.get('days_left', 0) <= 3:
            messagebox.showwarning(
                "تنبيه انتهاء الرخصة",
                f"⚠️ صلاحية اشتراكك تنتهي خلال {self.license_info['days_left']} أيام\n"
                f"الرجاء تجديد الاشتراك للحفاظ على الخدمة"
            )

    def disable_interface(self):
        """تعطيل واجهة المستخدم"""
        if hasattr(self, 'start_btn'):
            self.start_btn.config(state="disabled")
        if hasattr(self, 'settings_btn'):
            self.settings_btn.config(state="disabled")

    def enable_interface(self):
        """تفعيل واجهة المستخدم"""
        if hasattr(self, 'start_btn'):
            self.start_btn.config(state="normal")
        if hasattr(self, 'settings_btn'):
            self.settings_btn.config(state="normal")

    # ========================================================================
    # إعدادات التطبيق
    # ========================================================================

    def load_settings(self):
        """تحميل الإعدادات"""
        default_settings = {
            "images_folder": "",
            "names_file": "",
            "messages": ["مرحباً، هذه رسالة تجريبية"],
            "delay": 15,
            "restart_after": 50,
            "add_student_name": True,
            "message_box_coords": None,
            "dark_mode": True,
            "language": "ar"
        }

        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'rb') as f:
                    settings = pickle.load(f)
                    return {**default_settings, **settings}
        except:
            pass

        return default_settings

    def save_settings(self):
        """حفظ الإعدادات"""
        try:
            with open(self.settings_file, 'wb') as f:
                pickle.dump(self.settings, f)
            return True
        except:
            return False

    # ========================================================================
    # واجهة المستخدم
    # ========================================================================

    def setup_ui(self):
        """إنشاء واجهة المستخدم"""
        # تنظيف النافذة
        for widget in self.root.winfo_children():
            widget.destroy()

        # شريط العنوان
        self.create_title_bar()

        # منطقة المحتوى الرئيسية
        self.create_main_content()

        # شريط الحالة
        self.create_status_bar()

    def create_title_bar(self):
        """إنشاء شريط العنوان"""
        title_bar = tk.Frame(self.root, bg="#3498db", height=60)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        # العنوان
        title_label = tk.Label(
            title_bar,
            text="📱 WhatsApp Sender Pro - الإصدار الاحترافي",
            font=("Cairo", 16, "bold"),
            bg="#3498db",
            fg="white"
        )
        title_label.pack(side="left", padx=20)

        # حالة الرخصة
        self.license_status_label = tk.Label(
            title_bar,
            text="جاري التحقق...",
            font=("Cairo", 11),
            bg="#3498db",
            fg="white"
        )
        self.license_status_label.pack(side="right", padx=20)

        # أزرار التحكم
        control_frame = tk.Frame(title_bar, bg="#3498db")
        control_frame.pack(side="right", padx=10)

        ttk.Button(
            control_frame,
            text="ℹ️",
            command=self.show_about,
            width=3
        ).pack(side="left", padx=2)

        ttk.Button(
            control_frame,
            text="🔑",
            command=self.show_license_info,
            width=3
        ).pack(side="left", padx=2)

        ttk.Button(
            control_frame,
            text="⚙️",
            command=self.open_settings,
            width=3
        ).pack(side="left", padx=2)

    def create_main_content(self):
        """إنشاء المحتوى الرئيسي"""
        # إنشاء Notebook للتبويب
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # تبويب الإرسال
        self.send_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.send_tab, text="📤 الإرسال")
        self.create_send_tab()

        # تبويب الإعدادات
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="⚙️ الإعدادات")
        self.create_settings_tab()

        # تبويب التقارير
        self.reports_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.reports_tab, text="📊 التقارير")
        self.create_reports_tab()

    def create_send_tab(self):
        """إنشاء تبويب الإرسال"""
        # الإطار الرئيسي
        main_frame = ttk.Frame(self.send_tab, padding=20)
        main_frame.pack(fill="both", expand=True)

        # قسم الإعدادات الأساسية
        settings_frame = ttk.LabelFrame(
            main_frame,
            text="📁 الإعدادات الأساسية",
            padding=15
        )
        settings_frame.pack(fill="x", pady=(0, 15))

        # شبكة الإعدادات
        grid_frame = ttk.Frame(settings_frame)
        grid_frame.pack(fill="x")

        # صف 1: مجلد الصور
        ttk.Label(grid_frame, text="مجلد الصور:").grid(
            row=0, column=0, sticky="w", padx=5, pady=8
        )

        self.folder_var = tk.StringVar(value=self.settings.get("images_folder", ""))
        folder_entry = ttk.Entry(grid_frame, textvariable=self.folder_var, state="readonly")
        folder_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=8)

        ttk.Button(
            grid_frame,
            text="📂 اختيار",
            command=self.select_folder
        ).grid(row=0, column=2, padx=5, pady=8)

        # صف 2: ملف الأسماء
        ttk.Label(grid_frame, text="ملف الأسماء:").grid(
            row=1, column=0, sticky="w", padx=5, pady=8
        )

        self.names_var = tk.StringVar(value=self.settings.get("names_file", ""))
        names_entry = ttk.Entry(grid_frame, textvariable=self.names_var, state="readonly")
        names_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=8)

        ttk.Button(
            grid_frame,
            text="📄 اختيار",
            command=self.select_names_file
        ).grid(row=1, column=2, padx=5, pady=8)

        # قسم التحكم
        control_frame = ttk.LabelFrame(
            main_frame,
            text="🎮 التحكم",
            padding=15
        )
        control_frame.pack(fill="x", pady=(0, 15))

        # أزرار التحكم
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(pady=10)

        self.start_btn = ttk.Button(
            btn_frame,
            text="🚀 بدء الإرسال",
            command=self.start_sending,
            width=15,
            state="normal" if self.is_licensed else "disabled"
        )
        self.start_btn.pack(side="left", padx=10)

        self.pause_btn = ttk.Button(
            btn_frame,
            text="⏸️ إيقاف مؤقت",
            command=self.toggle_pause,
            state="disabled",
            width=15
        )
        self.pause_btn.pack(side="left", padx=10)

        self.stop_btn = ttk.Button(
            btn_frame,
            text="⏹️ إيقاف",
            command=self.stop_sending,
            state="disabled",
            width=15
        )
        self.stop_btn.pack(side="left", padx=10)

        # شريط التقدم
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill="x", pady=10)

        ttk.Label(progress_frame, text="التقدم:").pack(side="left", padx=(0, 10))

        self.progress = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=400,
            mode="determinate"
        )
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # العدادات
        counters_frame = ttk.Frame(progress_frame)
        counters_frame.pack(side="right")

        self.sent_label = ttk.Label(
            counters_frame,
            text="✅ تم: 0",
            font=("Cairo", 10)
        )
        self.sent_label.pack(side="left", padx=5)

        self.failed_label = ttk.Label(
            counters_frame,
            text="❌ فشل: 0",
            font=("Cairo", 10)
        )
        self.failed_label.pack(side="left", padx=5)

    def create_settings_tab(self):
        """إنشاء تبويب الإعدادات"""
        # محتوى الإعدادات
        settings_content = ttk.Frame(self.settings_tab, padding=20)
        settings_content.pack(fill="both", expand=True)

        # إضافة محتوى الإعدادات هنا
        ttk.Label(
            settings_content,
            text="إعدادات البرنامج",
            font=("Cairo", 14, "bold")
        ).pack(pady=10)

        # يمكنك إضافة المزيد من عناصر الإعدادات هنا

    def create_reports_tab(self):
        """إنشاء تبويب التقارير"""
        # محتوى التقارير
        reports_content = ttk.Frame(self.reports_tab, padding=20)
        reports_content.pack(fill="both", expand=True)

        # إضافة محتوى التقارير هنا
        ttk.Label(
            reports_content,
            text="تقارير الإرسال",
            font=("Cairo", 14, "bold")
        ).pack(pady=10)

        # يمكنك إضافة المزيد من عناصر التقارير هنا

    def create_status_bar(self):
        """إنشاء شريط الحالة"""
        status_bar = tk.Frame(self.root, height=30, bg="#2c3e50")
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)

        # معلومات الحالة
        self.status_text = tk.StringVar(value="جاهز للإرسال")
        status_label = tk.Label(
            status_bar,
            textvariable=self.status_text,
            bg="#2c3e50",
            fg="white",
            font=("Cairo", 10)
        )
        status_label.pack(side="left", padx=20)

        # معلومات النظام
        sys_info = tk.Label(
            status_bar,
            text=f"الإصدار: {self.version} | المطور: {self.developer}",
            bg="#2c3e50",
            fg="#bdc3c7",
            font=("Cairo", 9)
        )
        sys_info.pack(side="right", padx=20)

    # ========================================================================
    # وظائف التحكم
    # ========================================================================

    def select_folder(self):
        """اختيار مجلد الصور"""
        folder = filedialog.askdirectory(title="اختر مجلد الصور")
        if folder:
            self.folder_var.set(folder)
            self.settings["images_folder"] = folder
            self.save_settings()

    def select_names_file(self):
        """اختيار ملف الأسماء"""
        file = filedialog.askopenfilename(
            title="اختر ملف الأسماء",
            filetypes=[("ملفات نصية", "*.txt"), ("جميع الملفات", "*.*")]
        )
        if file:
            self.names_var.set(file)
            self.settings["names_file"] = file
            self.save_settings()

    def start_sending(self):
        """بدء عملية الإرسال"""
        # التحقق من الرخصة أولاً
        if not self.is_licensed:
            messagebox.showerror(
                "خطأ في الترخيص",
                "البرنامج غير مفعل!\nالرجاء تفعيل الرخصة أولاً."
            )
            self.show_activation_dialog()
            return

        # التحقق من الإعدادات
        if not self.validate_settings():
            return

        # تحديث واجهة المستخدم
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.stop_btn.config(state="normal")
        self.status_text.set("جاري الإرسال...")

        # بدء الإرسال في خيط منفصل
        send_thread = threading.Thread(target=self.send_process, daemon=True)
        send_thread.start()

    def validate_settings(self):
        """التحقق من صحة الإعدادات"""
        if not self.folder_var.get():
            messagebox.showerror("خطأ", "الرجاء اختيار مجلد الصور أولاً")
            return False
        return True

    def send_process(self):
        """عملية الإرسال الرئيسية"""
        try:
            # محاكاة عملية الإرسال
            total_items = 100
            for i in range(total_items):
                if self.should_stop:
                    break

                while self.is_paused:
                    time.sleep(0.5)

                # تحديث التقدم
                progress = (i + 1) / total_items * 100
                self.root.after(0, self.update_progress, progress, i + 1)

                time.sleep(0.1)  # محاكاة التأخير

            self.root.after(0, self.finish_sending)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("خطأ", str(e)))

    def update_progress(self, value, count):
        """تحديث شريط التقدم"""
        self.progress['value'] = value
        self.sent_label.config(text=f"✅ تم: {count}")

    def finish_sending(self):
        """إنهاء عملية الإرسال"""
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.status_text.set("اكتمل الإرسال")

    def toggle_pause(self):
        """تبديل حالة الإيقاف المؤقت"""
        if not hasattr(self, 'is_paused'):
            self.is_paused = False

        self.is_paused = not self.is_paused

        if self.is_paused:
            self.pause_btn.config(text="▶️ متابعة")
            self.status_text.set("متوقف مؤقتاً")
        else:
            self.pause_btn.config(text="⏸️ إيقاف مؤقت")
            self.status_text.set("جاري الإرسال...")

    def stop_sending(self):
        """إيقاف عملية الإرسال"""
        self.should_stop = True
        self.status_text.set("يتم الإيقاف...")

    # ========================================================================
    # وظائف النظام
    # ========================================================================

    def show_about(self):
        """عرض نافذة حول البرنامج"""
        about_text = f"""
        📱 WhatsApp Sender Pro

        الإصدار: {self.version}
        المطور: {self.developer}
        الدعم: {self.support_number}

        مميزات البرنامج:
        ✅ إرسال رسائل واتساب تلقائي
        ✅ دعم الصور والمستندات
        ✅ إدارة الأسماء والمستلمين
        ✅ تقارير مفصلة
        ✅ نظام ترخيص متكامل

        © 2024 جميع الحقوق محفوظة
        """

        about_window = tk.Toplevel(self.root)
        about_window.title("حول البرنامج")
        about_window.geometry("400x300")
        about_window.resizable(False, False)

        text_widget = tk.Text(
            about_window,
            wrap="word",
            font=("Cairo", 11),
            padx=15,
            pady=15
        )
        text_widget.insert("1.0", about_text)
        text_widget.config(state="disabled")
        text_widget.pack(fill="both", expand=True)

        ttk.Button(
            about_window,
            text="إغلاق",
            command=about_window.destroy
        ).pack(pady=10)

    def show_license_info(self):
        """عرض معلومات الرخصة"""
        if not self.license_manager:
            messagebox.showinfo("معلومات الرخصة", "نظام الترخيص غير متوفر")
            return

        info = self.license_manager.get_license_info()

        info_text = f"""
        🔑 معلومات الرخصة:

        الحالة: {'✅ مفعلة' if info.get('valid') else '❌ غير مفعلة'}
        الخطة: {info.get('plan', 'غير محدد')}
        تاريخ الانتهاء: {info.get('expiry_date', 'غير محدد')}
        الأيام المتبقية: {info.get('days_left', 0)}
        معرف الجهاز: {info.get('hwid', 'غير محدد')[:10]}...

        💰 طريقة الدفع:
        1. التحويل إلى: {self.support_number}
        2. الاسم: يوسف محمد زهير
        3. أرسل الإيصال على الواتساب
        """

        info_window = tk.Toplevel(self.root)
        info_window.title("معلومات الرخصة")
        info_window.geometry("500x350")
        info_window.resizable(False, False)

        text_widget = tk.Text(
            info_window,
            wrap="word",
            font=("Cairo", 11),
            bg="#f8f9fa",
            padx=15,
            pady=15
        )
        text_widget.insert("1.0", info_text)
        text_widget.config(state="disabled")
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)

        button_frame = tk.Frame(info_window)
        button_frame.pack(pady=10)

        if not info.get('valid'):
            ttk.Button(
                button_frame,
                text="🛒 شراء ترخيص",
                command=self.show_activation_dialog
            ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="إغلاق",
            command=info_window.destroy
        ).pack(side="right", padx=5)

    def open_settings(self):
        """فتح الإعدادات"""
        messagebox.showinfo("الإعدادات", "سيتم فتح إعدادات البرنامج")

    def run(self):
        """تشغيل البرنامج"""
        self.root.mainloop()


# ============================================================================
# نقطة الدخول الرئيسية
# ============================================================================

if __name__ == "__main__":
    # إنشاء النافذة الرئيسية
    root = tk.Tk()

    # إنشاء التطبيق
    app = WhatsAppSenderPro(root)

    # تشغيل التطبيق
    app.run()