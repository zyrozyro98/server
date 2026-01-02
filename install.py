"""
📦 برنامج تثبيت مرسل واتساب الاحترافي
"""

import subprocess
import sys
import os


def install_requirements():
    """تثبيت المتطلبات"""
    print("🔧 جاري تثبيت المتطلبات...")

    requirements = [
        "requests==2.31.0",
        "pyautogui==0.9.54",
        "pyperclip==1.8.2",
        "psutil==5.9.6",
        "Pillow==10.1.0"
    ]

    for package in requirements:
        try:
            print(f"📦 تثبيت {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ تم تثبيت {package}")
        except subprocess.CalledProcessError as e:
            print(f"❌ فشل تثبيت {package}: {e}")

    print("\n✅ اكتمل التثبيت!")
    print("\n📱 لتشغيل البرنامج:")
    print("python whatsapp_sender_pro.py")


if __name__ == "__main__":
    install_requirements()