"""
📦 برنامج إعداد وتشغيل النظام الكامل
"""

import os
import sys
import subprocess
import webbrowser
from tkinter import Tk, messagebox
import tkinter as tk

def check_requirements():
    """التحقق من المتطلبات"""
    required = ['requests', 'pyautogui', 'pyperclip', 'psutil', 'Pillow']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    return missing

def install_packages(packages):
    """تثبيت الحزم المطلوبة"""
    for package in packages:
        try:
            print(f"📦 جاري تثبيت {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ تم تثبيت {package}")
        except subprocess.CalledProcessError:
            print(f"❌ فشل تثبيت {package}")

def create_shortcut():
    """إنشاء اختصار للتطبيق"""
    if sys.platform == "win32":
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "مرسل واتساب.lnk")
        target = sys.executable
        wDir = os.path.dirname(sys.executable)
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = wDir
        shortcut.Arguments = f'"{os.path.abspath("whatsapp_sender_pro.py")}"'
        shortcut.IconLocation = target
        shortcut.save()
        
        print("📋 تم إنشاء اختصار على سطح المكتب")

def show_welcome():
    """عرض نافذة ترحيبية"""
    root = Tk()
    root.withdraw()  # إخفاء النافذة الرئيسية
    
    message = """
    🎉 مرحباً بك في نظام مرسل واتساب الاحترافي!
    
    📋 قبل البدء، تأكد من:
    
    1. ✅ اتصال مستقر بالإنترنت
    2. ✅ فتح واتساب ويب في المتصفح
    3. ✅ إعداد ملفات الصور/الأرقام مسبقاً
    
    ⚠️ تحذير:
    • استخدم البرنامج للأغراض المشروعة فقط
    • لا ترسل رسائل مزعجة أو غير مرغوب فيها
    • احترم خصوصية الآخرين
    
    📞 الدعم الفني: 771831482 967+
    
    اضغط موافق للمتابعة...
    """
    
    response = messagebox.askyesno("مرحباً بك", message)
    
    if response:
        root.destroy()
        return True
    else:
        root.destroy()
        return False

def main():
    """الدالة الرئيسية"""
    print("=" * 50)
    print("📱 إعداد نظام مرسل واتساب الاحترافي")
    print("=" * 50)
    
    # التحقق من المتطلبات
    print("\n🔍 جاري التحقق من المتطلبات...")
    missing = check_requirements()
    
    if missing:
        print(f"❌ الحزم المفقودة: {', '.join(missing)}")
        response = input("📦 هل تريد تثبيت الحزم المفقودة؟ (y/n): ")
        
        if response.lower() == 'y':
            install_packages(missing)
        else:
            print("❌ لا يمكن المتابعة بدون تثبيت الحزم المطلوبة")
            return
    
    # إنشاء الملفات
    print("\n📁 جاري إنشاء الملفات...")
    
    files_to_create = {
        'whatsapp_sender_pro.py': """# محتوى البرنامج الرئيسي (المذكور سابقاً)
# ضع هنا محتوى ملف whatsapp_sender_pro.py الكامل
""",
        'requirements.txt': """requests==2.31.0
pyautogui==0.9.54
pyperclip==1.8.2
psutil==5.9.6
Pillow==10.1.0
""",
        'readme.txt': """📖 دليل الاستخدام السريع:

1. ⭐ الاشتراك:
   - البرنامج يعمل بنظام اشتراكات شهرية
   - يجب تفعيله باستخدام مفتاح ترخيص
   - للدعم: 771831482 967+

2. 🔄 أنواع الإرسال:
   - إرسال صور مع رسائل: تحتاج لمجلد الصور وملف الأسماء
   - إرسال رسائل فقط: تحتاج فقط لملف الأرقام

3. 📁 إعدادات الملفات:
   - الصور: يجب أن تكون بأسماء الأرقام (مثال: 966501234567.jpg)
   - الأسماء: ملف نصي كل اسم في سطر
   - الأرقام: ملف نصي كل رقم في سطر

4. 💬 الرسائل:
   - أدخل مفتاح الدولة (مثال: +966 للسعودية)
   - حدد موقع مربع الرسالة في واتساب ويب

5. ⏰ التوقيت:
   - تأخير بين الرسائل: 5-10 ثواني (مثالي)
   - إعادة التشغيل: كل 50 رسالة لتجنب الحظر

⚡ نصائح مهمة:
• اختبر على رقم تجريبي أولاً
• استخدم الوضع البطيء للإرسال الكثيف
• احفظ الإعدادات المهمة

📞 الدعم الفني متاح يومياً 9:00 ص - 5:00 م
"""
    }
    
    for filename, content in files_to_create.items():
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ تم إنشاء {filename}")
    
    # إنشاء اختصار
    print("\n📋 جاري إنشاء الاختصارات...")
    create_shortcut()
    
    # عرض رسالة الترحيب
    print("\n🎯 جاري تحضير الواجهة...")
    if show_welcome():
        print("\n✅ تم الإعداد بنجاح!")
        print("\n🚀 لتشغيل البرنامج:")
        print("1. انقر نقراً مزدوجاً على 'مرسل واتساب' على سطح المكتب")
        print("2. أو شغّل: python whatsapp_sender_pro.py")
        print("\n📞 للدعم: 771831482 967+")
        
        # فتح دليل التطبيق
        if sys.platform == "win32":
            os.startfile(os.getcwd())
        elif sys.platform == "darwin":
            subprocess.Popen(["open", os.getcwd()])
        else:
            subprocess.Popen(["xdg-open", os.getcwd()])
    else:
        print("\n❌ تم إلغاء الإعداد")

if __name__ == "__main__":
    main()
