"""
👨‍💼 لوحة تحكم مشرفي نظام الاشتراكات
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
from datetime import datetime


class AdminPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("لوحة تحكم مشرفي الاشتراكات")
        self.root.geometry("1200x700")

        # إعدادات السيرفر
        self.server_url = "https://server-hxb7.onrender.com"
        self.api_key = "YES2Z8924_0"

        self.setup_ui()

    def setup_ui(self):
        """إعداد واجهة المستخدم"""
        # شريط العنوان
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        tk.Label(title_frame, text="👑 لوحة تحكم المشرفين - نظام الاشتراكات",
                 font=('Cairo', 18, 'bold'), bg="#2c3e50", fg="white").pack(expand=True)

        # شريط الأدوات
        toolbar = tk.Frame(self.root, bg="#34495e", height=40)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        tk.Button(toolbar, text="🔄 تحديث البيانات", command=self.refresh_data,
                  bg="#3498db", fg="white", font=('Cairo', 10)).pack(side="left", padx=10, pady=5)

        tk.Button(toolbar, text="➕ إنشاء ترخيص جديد", command=self.create_license_dialog,
                  bg="#27ae60", fg="white", font=('Cairo', 10)).pack(side="left", padx=10, pady=5)

        # الإطار الرئيسي
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # إنشاء تبويبات
        notebook = ttk.Notebook(main_frame)

        # تبويب التراخيص
        licenses_tab = ttk.Frame(notebook)
        notebook.add(licenses_tab, text="📋 جميع التراخيص")

        # إنشاء جدول التراخيص
        columns = ("المفتاح", "العميل", "البريد", "تاريخ البدء",
                   "تاريخ الانتهاء", "النوع", "الحالة", "الأجهزة", "الأقصى")

        self.licenses_tree = ttk.Treeview(licenses_tab, columns=columns, show="headings", height=20)

        for col in columns:
            self.licenses_tree.heading(col, text=col)
            self.licenses_tree.column(col, width=120)

        scrollbar = ttk.Scrollbar(licenses_tab, orient="vertical", command=self.licenses_tree.yview)
        self.licenses_tree.configure(yscrollcommand=scrollbar.set)

        self.licenses_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # تبويب الإحصائيات
        stats_tab = ttk.Frame(notebook)
        notebook.add(stats_tab, text="📊 الإحصائيات")

        self.setup_stats_tab(stats_tab)

        notebook.pack(fill="both", expand=True)

        # تحميل البيانات الأولية
        self.refresh_data()

    def setup_stats_tab(self, parent):
        """إعداد تبويب الإحصائيات"""
        stats_frame = tk.Frame(parent, padx=20, pady=20)
        stats_frame.pack(fill="both", expand=True)

        # بطاقات الإحصائيات
        cards_frame = tk.Frame(stats_frame)
        cards_frame.pack(fill="x", pady=(0, 20))

        # تخزين البطاقات في قائمة
        self.stat_cards_frames = []
        self.stat_cards_labels = {}
        
        # إنشاء البطاقات
        card_info = [
            ("إجمالي التراخيص", "0", "#3498db", "total_licenses"),
            ("التراخيص النشطة", "0", "#27ae60", "active_licenses"),
            ("التراخيص المنتهية", "0", "#e74c3c", "expired_licenses"),
            ("الأجهزة المسجلة", "0", "#9b59b6", "total_devices")
        ]
        
        for i, (title, value, color, key) in enumerate(card_info):
            card_frame = tk.Frame(cards_frame, bg=color, relief="raised", borderwidth=2)
            
            tk.Label(card_frame, text=title, font=('Cairo', 12, 'bold'),
                    bg=color, fg="white").pack(pady=(10, 5))
            
            value_label = tk.Label(card_frame, text=value, font=('Cairo', 24, 'bold'),
                                  bg=color, fg="white")
            value_label.pack(pady=(0, 10))
            
            # تخزين المرجع في القواميس
            self.stat_cards_frames.append(card_frame)
            self.stat_cards_labels[key] = value_label
            
            # وضع البطاقة في الشبكة
            card_frame.grid(row=0, column=i, padx=10, sticky="nsew")
            cards_frame.columnconfigure(i, weight=1)

        # مخطط التراخيص حسب النوع
        type_frame = tk.LabelFrame(stats_frame, text="📈 توزيع التراخيص حسب النوع",
                                   font=('Cairo', 12, 'bold'), padx=15, pady=15)
        type_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.type_chart = tk.Text(type_frame, height=10, font=('Cairo', 10))
        self.type_chart.pack(fill="both", expand=True)

        # مخطط التراخيص حسب الحالة
        status_frame = tk.LabelFrame(stats_frame, text="📊 حالة التراخيص",
                                     font=('Cairo', 12, 'bold'), padx=15, pady=15)
        status_frame.pack(fill="both", expand=True)

        self.status_chart = tk.Text(status_frame, height=8, font=('Cairo', 10))
        self.status_chart.pack(fill="both", expand=True)

    def create_stat_card(self, parent, title, value, color):
        """إنشاء بطاقة إحصائية"""
        card = tk.Frame(parent, bg=color, relief="raised", borderwidth=2)

        tk.Label(card, text=title, font=('Cairo', 12, 'bold'),
                 bg=color, fg="white").pack(pady=(10, 5))

        value_label = tk.Label(card, text=value, font=('Cairo', 24, 'bold'),
                               bg=color, fg="white")
        value_label.pack(pady=(0, 10))

        return card, value_label

    def refresh_data(self):
        """تحديث جميع البيانات"""
        try:
            # جلب جميع التراخيص
            headers = {'Authorization': f'Bearer {self.api_key}'}
            response = requests.get(f"{self.server_url}/api/v1/admin/licenses",
                                    headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    self.update_licenses_table(data['licenses'])
                    self.update_statistics(data['licenses'])
                else:
                    messagebox.showerror("خطأ", data['message'])
            else:
                messagebox.showerror("خطأ", f"فشل الاتصال: {response.status_code}")

        except requests.exceptions.ConnectionError:
            messagebox.showerror("خطأ", "لا يمكن الاتصال بالسيرفر")
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ: {str(e)}")

    def update_licenses_table(self, licenses):
        """تحديث جدول التراخيص"""
        # مسح البيانات القديمة
        for item in self.licenses_tree.get_children():
            self.licenses_tree.delete(item)

        # إضافة البيانات الجديدة
        for license in licenses:
            # تحديد لون الصف حسب الحالة
            tags = ()
            if license['is_expired']:
                tags = ('expired',)
            elif license['status'] == 'active':
                tags = ('active',)

            values = (
                license['license_key'],
                license['customer_name'],
                license['customer_email'],
                license['start_date'][:10],
                license['expiry_date'][:10],
                license['plan_type'],
                license['status'],
                f"{license['devices_registered']}/{license['max_devices']}",
                license['max_devices']
            )

            self.licenses_tree.insert("", "end", values=values, tags=tags)

        # تخصيص الألوان
        self.licenses_tree.tag_configure('expired', background='#ffcccc')
        self.licenses_tree.tag_configure('active', background='#ccffcc')

    def update_statistics(self, licenses):
        """تحديث الإحصائيات"""
        total = len(licenses)
        active = sum(1 for l in licenses if not l['is_expired'] and l['status'] == 'active')
        expired = sum(1 for l in licenses if l['is_expired'])
        total_devices = sum(l['devices_registered'] for l in licenses)

        # تحديث البطاقات
        self.stat_cards_labels['total_licenses'].config(text=str(total))
        self.stat_cards_labels['active_licenses'].config(text=str(active))
        self.stat_cards_labels['expired_licenses'].config(text=str(expired))
        self.stat_cards_labels['total_devices'].config(text=str(total_devices))

        # تحديث مخطط النوع
        plan_types = {}
        for license in licenses:
            plan_type = license['plan_type']
            plan_types[plan_type] = plan_types.get(plan_type, 0) + 1

        type_text = "📊 توزيع التراخيص حسب النوع:\n\n"
        for plan_type, count in plan_types.items():
            percentage = (count / total) * 100 if total > 0 else 0
            type_text += f"{plan_type}: {count} ترخيص ({percentage:.1f}%)\n"
            type_text += "▰" * int(percentage / 5) + "\n\n"

        self.type_chart.delete("1.0", tk.END)
        self.type_chart.insert("1.0", type_text)

        # تحديث مخطط الحالة
        status_text = "📈 حالة التراخيص:\n\n"
        status_text += f"✅ نشطة: {active} ({active / total * 100:.1f}%)\n"
        status_text += f"❌ منتهية: {expired} ({expired / total * 100:.1f}%)\n\n"

        active_bars = "▰" * int((active / total) * 20) if total > 0 else ""
        expired_bars = "▰" * int((expired / total) * 20) if total > 0 else ""

        status_text += f"النشطة:  {active_bars}\n"
        status_text += f"المنتهية: {expired_bars}"

        self.status_chart.delete("1.0", tk.END)
        self.status_chart.insert("1.0", status_text)

    def create_license_dialog(self):
        """نافذة إنشاء ترخيص جديد"""
        dialog = tk.Toplevel(self.root)
        dialog.title("إنشاء ترخيص جديد")
        dialog.geometry("400x350")
        dialog.resizable(False, False)

        # مركزة النافذة
        dialog.transient(self.root)
        dialog.grab_set()

        # محتوى النافذة
        content = tk.Frame(dialog, padx=20, pady=20)
        content.pack(fill="both", expand=True)

        tk.Label(content, text="بريد العميل:", font=('Cairo', 11)).grid(row=0, column=0, sticky="w", pady=10)
        email_entry = tk.Entry(content, font=('Cairo', 11), width=30)
        email_entry.grid(row=0, column=1, pady=10)

        tk.Label(content, text="نوع الخطة:", font=('Cairo', 11)).grid(row=1, column=0, sticky="w", pady=10)
        plan_var = tk.StringVar(value="basic")
        plan_combo = ttk.Combobox(content, textvariable=plan_var,
                                  values=["basic", "standard", "premium"],
                                  state="readonly", width=20)
        plan_combo.grid(row=1, column=1, pady=10)

        tk.Label(content, text="المدة (أيام):", font=('Cairo', 11)).grid(row=2, column=0, sticky="w", pady=10)
        duration_var = tk.StringVar(value="30")
        duration_entry = tk.Entry(content, textvariable=duration_var, font=('Cairo', 11), width=10)
        duration_entry.grid(row=2, column=1, pady=10)

        tk.Label(content, text="الحد الأقصى للأجهزة:", font=('Cairo', 11)).grid(row=3, column=0, sticky="w", pady=10)
        devices_var = tk.StringVar(value="1")
        devices_entry = tk.Entry(content, textvariable=devices_var, font=('Cairo', 11), width=10)
        devices_entry.grid(row=3, column=1, pady=10)

        # رسالة النتيجة
        result_label = tk.Label(content, text="", font=('Cairo', 10), fg="#e74c3c")
        result_label.grid(row=4, column=0, columnspan=2, pady=10)

        def create_license():
            """إنشاء الترخيص"""
            email = email_entry.get().strip()
            plan_type = plan_var.get()

            try:
                duration = int(duration_var.get())
                max_devices = int(devices_var.get())
            except ValueError:
                result_label.config(text="❌ الرجاء إدخال أرقام صحيحة للمدة والأجهزة")
                return

            if not email:
                result_label.config(text="❌ الرجاء إدخال بريد العميل")
                return

            result_label.config(text="🔄 جاري إنشاء الترخيص...", fg="#f39c12")
            dialog.update()

            try:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }

                payload = {
                    'customer_email': email,
                    'plan_type': plan_type,
                    'duration_days': duration,
                    'max_devices': max_devices
                }

                response = requests.post(
                    f"{self.server_url}/api/v1/licenses/create",
                    json=payload,
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if data['success']:
                        result_label.config(text=f"✅ تم إنشاء الترخيص:\n{data['license_key']}", fg="#27ae60")

                        # تحديث البيانات بعد 2 ثانية
                        dialog.after(2000, lambda: [dialog.destroy(), self.refresh_data()])
                    else:
                        result_label.config(text=f"❌ {data['message']}", fg="#e74c3c")
                else:
                    result_label.config(text=f"❌ خطأ في السيرفر: {response.status_code}", fg="#e74c3c")

            except requests.exceptions.ConnectionError:
                result_label.config(text="❌ لا يمكن الاتصال بالسيرفر", fg="#e74c3c")
            except Exception as e:
                result_label.config(text=f"❌ خطأ: {str(e)}", fg="#e74c3c")

        # أزرار
        btn_frame = tk.Frame(content)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)

        tk.Button(btn_frame, text="إنشاء", command=create_license,
                  bg="#27ae60", fg="white", font=('Cairo', 11),
                  width=10).pack(side="left", padx=10)

        tk.Button(btn_frame, text="إلغاء", command=dialog.destroy,
                  bg="#e74c3c", fg="white", font=('Cairo', 11),
                  width=10).pack(side="left", padx=10)

    def run(self):
        """تشغيل لوحة التحكم"""
        self.root.mainloop()


if __name__ == "__main__":
    app = AdminPanel()
    app.run()
