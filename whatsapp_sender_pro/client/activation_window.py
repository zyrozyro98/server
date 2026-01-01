"""
نافذة تفعيل البرنامج
"""

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from datetime import datetime, timedelta


class ActivationWindow:
    def __init__(self, parent, license_manager, on_activate_callback=None):
        self.parent = parent
        self.license_manager = license_manager
        self.on_activate_callback = on_activate_callback

        self.window = tk.Toplevel(parent)
        self.window.title("💎 تفعيل WhatsApp Sender Pro")
        self.window.geometry("650x600")
        self.window.resizable(False, False)
        self.window.configure(bg="#2c3e50")

        # جعل النافذة مركزية
        self.center_window()

        # منع الوصول للنافذة الرئيسية
        self.window.transient(parent)
        self.window.grab_set()

        # إنشاء الواجهة
        self.create_ui()

    def center_window(self):
        """توسيط النافذة"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def create_ui(self):
        """إنشاء واجهة المستخدم"""
        # إطار العنوان
        self.create_header()

        # الإطار الرئيسي
        self.create_main_content()

        # إطار التفعيل
        self.create_activation_section()

        # إطار الدفع
        self.create_payment_section()

        # أزرار التحكم
        self.create_buttons()

    def create_header(self):
        """إنشاء رأس النافذة"""
        header_frame = tk.Frame(self.window, bg="#3498db", height=100)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        # العنوان الرئيسي
        title_label = tk.Label(
            header_frame,
            text="💎 WhatsApp Sender Pro",
            font=("Cairo", 20, "bold"),
            bg="#3498db",
            fg="white"
        )
        title_label.pack(expand=True)

        # العنوان الفرعي
        subtitle_label = tk.Label(
            header_frame,
            text="الإصدار الاحترافي - نظام الاشتراكات",
            font=("Cairo", 12),
            bg="#3498db",
            fg="#ecf0f1"
        )
        subtitle_label.pack()

        # معلومات الإصدار
        version_label = tk.Label(
            header_frame,
            text="v2.0.0 | © 2024",
            font=("Cairo", 9),
            bg="#3498db",
            fg="#bdc3c7"
        )
        version_label.pack(side="right", padx=10, pady=5)

    def create_main_content(self):
        """إنشاء المحتوى الرئيسي"""
        # إطار المحتوى
        content_frame = tk.Frame(self.window, bg="#2c3e50", padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)

        # قسم معلومات الجهاز
        device_frame = tk.LabelFrame(
            content_frame,
            text="📱 معلومات جهازك",
            font=("Cairo", 12, "bold"),
            bg="#34495e",
            fg="white",
            padx=15,
            pady=15
        )
        device_frame.pack(fill="x", pady=(0, 15))

        # جمع معلومات الجهاز
        device_info = self.get_device_info()

        # عرض معلومات الجهاز
        for i, (key, value) in enumerate(device_info.items()):
            frame = tk.Frame(device_frame, bg="#34495e")
            frame.pack(fill="x", pady=2)

            tk.Label(
                frame,
                text=f"• {key}:",
                font=("Cairo", 10),
                bg="#34495e",
                fg="#3498db",
                width=15,
                anchor="w"
            ).pack(side="left")

            tk.Label(
                frame,
                text=value,
                font=("Cairo", 10, "bold"),
                bg="#34495e",
                fg="#ecf0f1",
                anchor="w"
            ).pack(side="left", fill="x", expand=True)

    def get_device_info(self):
        """الحصول على معلومات الجهاز"""
        info = {
            "معرف الجهاز": self.license_manager.hwid[:20] + "...",
            "نظام التشغيل": self.license_manager.system_info.get('os', 'غير معروف'),
            "اسم المستخدم": self.license_manager.system_info.get('username', 'غير معروف'),
            "اسم الجهاز": self.license_manager.system_info.get('hostname', 'غير معروف'),
            "تاريخ التحقق": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        return info

    def create_activation_section(self):
        """إنشاء قسم التفعيل"""
        # إطار التفعيل
        activation_frame = tk.LabelFrame(
            self.window,
            text="🔑 تفعيل البرنامج",
            font=("Cairo", 12, "bold"),
            bg="#34495e",
            fg="white",
            padx=15,
            pady=15
        )
        activation_frame.pack(fill="x", padx=20, pady=(0, 15))

        # خيارات الاشتراك
        plans_frame = tk.Frame(activation_frame, bg="#34495e")
        plans_frame.pack(fill="x", pady=10)

        self.plan_var = tk.StringVar(value="monthly")

        # خيارات الاشتراك
        plans = [
            ("💰 اشتراك شهري", "monthly", "10$", "مميزات كاملة، تجديد شهري"),
            ("💎 اشتراك سنوي", "yearly", "100$", "توفير 20%، مميزات كاملة"),
            ("🆓 تجريبي", "trial", "مجاناً", "7 أيام تجريبية")
        ]

        for plan_name, plan_value, price, description in plans:
            plan_frame = tk.Frame(plans_frame, bg="#34495e")
            plan_frame.pack(fill="x", pady=5)

            # زر الاختيار
            tk.Radiobutton(
                plan_frame,
                text="",
                variable=self.plan_var,
                value=plan_value,
                bg="#34495e",
                fg="white",
                selectcolor="#2c3e50",
                activebackground="#34495e"
            ).pack(side="left", padx=(0, 10))

            # معلومات الخطة
            info_frame = tk.Frame(plan_frame, bg="#34495e")
            info_frame.pack(side="left", fill="x", expand=True)

            tk.Label(
                info_frame,
                text=plan_name,
                font=("Cairo", 11, "bold"),
                bg="#34495e",
                fg="#f1c40f" if plan_value == "yearly" else "white",
                anchor="w"
            ).pack(anchor="w")

            tk.Label(
                info_frame,
                text=f"{price} - {description}",
                font=("Cairo", 9),
                bg="#34495e",
                fg="#bdc3c7",
                anchor="w"
            ).pack(anchor="w")

    def create_payment_section(self):
        """إنشاء قسم الدفع"""
        # إطار الدفع
        payment_frame = tk.LabelFrame(
            self.window,
            text="💳 طريقة الدفع والتفعيل",
            font=("Cairo", 12, "bold"),
            bg="#34495e",
            fg="white",
            padx=15,
            pady=15
        )
        payment_frame.pack(fill="x", padx=20, pady=(0, 15))

        # معلومات الدفع
        payment_text = """
        📋 خطوات الدفع والتفعيل:

        1️⃣ اختر نوع الاشتراك المطلوب
        2️⃣ قم بالتحويل المالي إلى:
           - الرقم: 771831482
           - الاسم: يوسف محمد علي حمود زهير

        3️⃣ أرسل إيصال التحويل على الواتساب:
           - الرقم: 771831482
           - مع كتابة: "تفعيل WhatsApp Sender"

        4️⃣ ستصلك مفتاح التفعيل خلال 24 ساعة
        5️⃣ أدخل المفتاح في الحقل أدناه

        ⏰ وقت التفعيل: 24 ساعة كحد أقصى
        📞 للاستفسار: 771831482
        """

        payment_label = tk.Label(
            payment_frame,
            text=payment_text,
            font=("Cairo", 10),
            bg="#34495e",
            fg="#ecf0f1",
            justify="left",
            anchor="w"
        )
        payment_label.pack(fill="x", pady=10)

        # حقل إدخال مفتاح التفعيل
        key_frame = tk.Frame(payment_frame, bg="#34495e")
        key_frame.pack(fill="x", pady=(10, 0))

        tk.Label(
            key_frame,
            text="🔑 مفتاح التفعيل:",
            font=("Cairo", 11),
            bg="#34495e",
            fg="white"
        ).pack(anchor="w")

        self.key_entry = tk.Entry(
            key_frame,
            font=("Cairo", 12),
            width=40,
            bg="#2c3e50",
            fg="white",
            insertbackground="white"
        )
        self.key_entry.pack(fill="x", pady=5)
        self.key_entry.focus_set()

    def create_buttons(self):
        """إنشاء أزرار التحكم"""
        button_frame = tk.Frame(self.window, bg="#2c3e50", padx=20, pady=20)
        button_frame.pack(fill="x")

        # أزرار اليسار
        left_frame = tk.Frame(button_frame, bg="#2c3e50")
        left_frame.pack(side="left")

        # زر التجريب المجاني
        trial_btn = tk.Button(
            left_frame,
            text="🆓 تجربة مجانية",
            font=("Cairo", 11),
            bg="#3498db",
            fg="white",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.start_trial
        )
        trial_btn.pack(side="left", padx=5)

        # زر شراء اشتراك
        buy_btn = tk.Button(
            left_frame,
            text="🛒 شراء اشتراك",
            font=("Cairo", 11),
            bg="#e74c3c",
            fg="white",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.open_payment_page
        )
        buy_btn.pack(side="left", padx=5)

        # أزرار اليمين
        right_frame = tk.Frame(button_frame, bg="#2c3e50")
        right_frame.pack(side="right")

        # زر إلغاء
        cancel_btn = tk.Button(
            right_frame,
            text="❌ إغلاق",
            font=("Cairo", 11),
            bg="#7f8c8d",
            fg="white",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.window.destroy
        )
        cancel_btn.pack(side="right", padx=5)

        # زر التفعيل
        activate_btn = tk.Button(
            right_frame,
            text="✅ تفعيل الآن",
            font=("Cairo", 11, "bold"),
            bg="#27ae60",
            fg="white",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.activate_license
        )
        activate_btn.pack(side="right", padx=5)

    def activate_license(self):
        """تفعيل الرخصة"""
        license_key = self.key_entry.get().strip()

        if not license_key:
            messagebox.showwarning("تنبيه", "الرجاء إدخال مفتاح التفعيل")
            return

        # إظهار نافذة التحميل
        loading_window = tk.Toplevel(self.window)
        loading_window.title("جاري التفعيل...")
        loading_window.geometry("300x150")
        loading_window.resizable(False, False)
        loading_window.configure(bg="#2c3e50")
        loading_window.transient(self.window)

        # رسالة التحميل
        tk.Label(
            loading_window,
            text="🔄 جاري تفعيل الرخصة...",
            font=("Cairo", 12),
            bg="#2c3e50",
            fg="white"
        ).pack(expand=True)

        # شريط التقدم
        progress = ttk.Progressbar(
            loading_window,
            orient="horizontal",
            length=250,
            mode="indeterminate"
        )
        progress.pack(pady=10)
        progress.start(10)

        loading_window.update()

        # محاولة التفعيل
        success, message = self.license_manager.activate_license(license_key)

        # إغلاق نافذة التحميل
        loading_window.destroy()

        if success:
            messagebox.showinfo("نجاح", f"✅ {message}")
            if self.on_activate_callback:
                self.on_activate_callback()
            self.window.destroy()
        else:
            messagebox.showerror("خطأ", f"❌ {message}")

    def start_trial(self):
        """بدء الفترة التجريبية"""
        # إظهار رسالة تأكيد
        confirm = messagebox.askyesno(
            "تجريبية مجانية",
            "هل تريد تفعيل النسخة التجريبية؟\n\n"
            "⚠️ ملاحظة:\n"
            "- المدة: 7 أيام مجاناً\n"
            "- بعض المميزات قد تكون محدودة\n"
            "- بعد انتهاء المدة يجب شراء اشتراك"
        )

        if confirm:
            # محاولة الحصول على ترخيص تجريبي
            success, message = self.license_manager.get_trial_license()

            if success:
                messagebox.showinfo("نجاح", f"✅ {message}")
                if self.on_activate_callback:
                    self.on_activate_callback()
                self.window.destroy()
            else:
                messagebox.showerror("خطأ", f"❌ {message}")

    def open_payment_page(self):
        """فتح صفحة الدفع"""
        plan = self.plan_var.get()

        # تحديد سعر الخطة
        prices = {
            "monthly": "10",
            "yearly": "100"
        }

        price = prices.get(plan, "10")

        # إنشاء رسالة الدفع
        payment_message = (
            f"💳 طلب اشتراك WhatsApp Sender Pro\n\n"
            f"🔹 الخطة: {'شهري' if plan == 'monthly' else 'سنوي'}\n"
            f"🔹 السعر: {price}$\n"
            f"🔹 HWID: {self.license_manager.hwid[:15]}...\n\n"
            f"📞 للدفع: 771831482\n"
            f"👤 الاسم: يوسف محمد زهير\n\n"
            f"بعد الدفع، أرسل الإيصال على الواتساب"
        )

        # عرض رسالة الدفع
        messagebox.showinfo("تفاصيل الدفع", payment_message)

        # يمكنك إضافة رابط لصفحة دفع حقيقية هنا
        # webbrowser.open("https://your-payment-link.com")