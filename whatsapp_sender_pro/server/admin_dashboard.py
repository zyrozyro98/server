"""
لوحة تحكم المسؤول - واجهة ويب
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import os
import json
from datetime import datetime, timedelta
from database import DatabaseManager

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
db = DatabaseManager()

# مفتاح الدخول للمسؤول
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')


def login_required(f):
    """ميدلوير للتحقق من تسجيل الدخول"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل دخول المسؤول"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))

        return render_template('admin/login.html', error='بيانات الدخول غير صحيحة')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """تسجيل خروج المسؤول"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@login_required
def dashboard():
    """لوحة التحكم الرئيسية"""
    # إحصائيات النظام
    stats = db.get_license_stats()

    # التراخيص الحديثة
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT l.*, u.email, u.name 
    FROM licenses l
    LEFT JOIN users u ON l.user_id = u.id
    ORDER BY l.created_at DESC
    LIMIT 10
    ''')

    recent_licenses = cursor.fetchall()

    # النشاطات الحديثة
    recent_activity = db.get_recent_activity(10)

    conn.close()

    return render_template('admin/dashboard.html',
                           stats=stats,
                           recent_licenses=recent_licenses,
                           recent_activity=recent_activity)


@admin_bp.route('/licenses')
@login_required
def licenses():
    """صفحة إدارة التراخيص"""
    search = request.args.get('search', '')
    status_filter = request.args.get('status', 'all')

    conn = db.get_connection()
    cursor = conn.cursor()

    query = '''
    SELECT l.*, u.email, u.name, u.whatsapp_number,
           COUNT(ud.id) as device_count
    FROM licenses l
    LEFT JOIN users u ON l.user_id = u.id
    LEFT JOIN user_devices ud ON l.id = ud.license_id
    WHERE 1=1
    '''

    params = []

    if search:
        query += ' AND (l.license_key LIKE ? OR u.email LIKE ? OR u.name LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])

    if status_filter != 'all':
        query += ' AND l.status = ?'
        params.append(status_filter)

    query += ' GROUP BY l.id ORDER BY l.created_at DESC'

    cursor.execute(query, params)
    licenses_list = cursor.fetchall()

    conn.close()

    return render_template('admin/licenses.html',
                           licenses=licenses_list,
                           search=search,
                           status_filter=status_filter)


@admin_bp.route('/license/create', methods=['GET', 'POST'])
@login_required
def create_license():
    """إنشاء رخصة جديدة"""
    if request.method == 'POST':
        license_data = {
            'license_key': request.form.get('license_key'),
            'plan_type': request.form.get('plan_type'),
            'license_type': request.form.get('license_type'),
            'duration_days': int(request.form.get('duration_days', 30)),
            'max_devices': int(request.form.get('max_devices', 1)),
            'user_email': request.form.get('user_email'),
            'user_name': request.form.get('user_name'),
            'features': {
                'basic_sending': 'basic_sending' in request.form,
                'unlimited_messages': 'unlimited_messages' in request.form,
                'scheduling': 'scheduling' in request.form,
                'reports': 'reports' in request.form
            }
        }

        # حساب تاريخ الانتهاء
        if license_data['license_type'] == 'trial':
            license_data['duration_days'] = 7

        license_data['expiry_date'] = datetime.now() + timedelta(days=license_data['duration_days'])

        # إنشاء المستخدم إذا كان هناك بريد إلكتروني
        user_id = None
        if license_data['user_email']:
            user = db.get_user(license_data['user_email'])
            if not user:
                user_id = db.create_user({
                    'email': license_data['user_email'],
                    'name': license_data['user_name']
                })
            else:
                user_id = user['id']

        license_data['user_id'] = user_id

        # إنشاء الرخصة
        license_id = db.create_license(license_data)

        if license_id:
            return redirect(url_for('admin.licenses'))

        return render_template('admin/create_license.html', error='فشل في إنشاء الرخصة')

    return render_template('admin/create_license.html')


@admin_bp.route('/license/<license_key>/edit', methods=['GET', 'POST'])
@login_required
def edit_license(license_key):
    """تعديل رخصة"""
    license_data = db.get_license(license_key)

    if not license_data:
        return redirect(url_for('admin.licenses'))

    if request.method == 'POST':
        update_data = {
            'plan_type': request.form.get('plan_type'),
            'license_type': request.form.get('license_type'),
            'status': request.form.get('status'),
            'max_devices': int(request.form.get('max_devices', 1))
        }

        # تحديث تاريخ الانتهاء إذا تم تغييره
        new_expiry = request.form.get('expiry_date')
        if new_expiry:
            update_data['expiry_date'] = datetime.fromisoformat(new_expiry)

        # تحديث الميزات
        features = {
            'basic_sending': 'basic_sending' in request.form,
            'unlimited_messages': 'unlimited_messages' in request.form,
            'scheduling': 'scheduling' in request.form,
            'reports': 'reports' in request.form
        }
        update_data['features'] = json.dumps(features)

        success = db.update_license(license_key, update_data)

        if success:
            return redirect(url_for('admin.licenses'))

        return render_template('admin/edit_license.html',
                               license=license_data,
                               error='فشل في تحديث الرخصة')

    return render_template('admin/edit_license.html', license=license_data)


@admin_bp.route('/license/<license_key>/delete')
@login_required
def delete_license(license_key):
    """حذف رخصة"""
    success = db.delete_license(license_key)

    if success:
        # تسجيل النشاط
        db.log_activity({
            'action': 'license_deleted',
            'details': {'license_key': license_key}
        })

    return redirect(url_for('admin.licenses'))


@admin_bp.route('/users')
@login_required
def users():
    """صفحة إدارة المستخدمين"""
    search = request.args.get('search', '')

    conn = db.get_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM users WHERE 1=1'
    params = []

    if search:
        query += ' AND (email LIKE ? OR name LIKE ? OR whatsapp_number LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])

    query += ' ORDER BY created_at DESC'

    cursor.execute(query, params)
    users_list = cursor.fetchall()

    # الحصول على عدد التراخيص لكل مستخدم
    for user in users_list:
        cursor.execute('SELECT COUNT(*) as license_count FROM licenses WHERE user_id = ?', (user['id'],))
        user['license_count'] = cursor.fetchone()['license_count']

    conn.close()

    return render_template('admin/users.html', users=users_list, search=search)


@admin_bp.route('/user/<int:user_id>')
@login_required
def user_detail(user_id):
    """تفاصيل المستخدم"""
    conn = db.get_connection()
    cursor = conn.cursor()

    # معلومات المستخدم
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return redirect(url_for('admin.users'))

    # تراخيص المستخدم
    cursor.execute('''
    SELECT l.*, COUNT(ud.id) as device_count
    FROM licenses l
    LEFT JOIN user_devices ud ON l.id = ud.license_id
    WHERE l.user_id = ?
    GROUP BY l.id
    ORDER BY l.created_at DESC
    ''', (user_id,))

    user_licenses = cursor.fetchall()

    # أجهزة المستخدم
    cursor.execute('''
    SELECT ud.*, l.license_key
    FROM user_devices ud
    JOIN licenses l ON ud.license_id = l.id
    WHERE ud.user_id = ?
    ORDER BY ud.last_seen DESC
    ''', (user_id,))

    user_devices = cursor.fetchall()

    conn.close()

    return render_template('admin/user_detail.html',
                           user=user,
                           licenses=user_licenses,
                           devices=user_devices)


@admin_bp.route('/payments')
@login_required
def payments():
    """صفحة المدفوعات"""
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT p.*, u.email, u.name, l.license_key
    FROM payments p
    LEFT JOIN users u ON p.user_id = u.id
    LEFT JOIN licenses l ON p.license_id = l.id
    ORDER BY p.created_at DESC
    ''')

    payments_list = cursor.fetchall()

    # إحصائيات المدفوعات
    cursor.execute('''
    SELECT 
        COUNT(*) as total,
        SUM(amount) as total_amount,
        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as completed_amount
    FROM payments
    ''')

    stats = cursor.fetchone()

    conn.close()

    return render_template('admin/payments.html',
                           payments=payments_list,
                           stats=stats)


@admin_bp.route('/activity')
@login_required
def activity():
    """سجل النشاطات"""
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT a.*, u.email, l.license_key
    FROM activity_logs a
    LEFT JOIN users u ON a.user_id = u.id
    LEFT JOIN licenses l ON a.license_id = l.id
    ORDER BY a.created_at DESC
    LIMIT 100
    ''')

    activities = cursor.fetchall()

    conn.close()

    return render_template('admin/activity.html', activities=activities)


@admin_bp.route('/api/stats')
@login_required
def api_stats():
    """API للإحصائيات"""
    stats = db.get_license_stats()
    return jsonify(stats)