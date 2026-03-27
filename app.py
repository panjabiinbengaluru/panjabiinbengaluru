import os
import re
import string
import random
from datetime import datetime, timezone, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'panjabi-in-bengaluru-secret-2024')

# ── MongoDB Atlas ────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get('MONGO_URI', '')

def get_db():
    """Return the MembershipApplications database (lazy connection)."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return client['MembershipApplications']

TEAM_MEMBERS = [
    {
        'name': 'Mehakdeep Singh',
        'role': 'Co-Founder & Community Lead',
        'bio': 'Passionate about building bridges between Punjabis across India. Mehakdeep leads community strategy, events, and growth initiatives for Panjabi in Bengaluru.',
        'instagram': 'https://www.instagram.com/mehak.shokar/',
        'instagram_handle': '@mehak.shokar',
        'initials': 'MS',
    },
    {
        'name': 'Karun Pabbi',
        'role': 'Co-Founder & Operations Head',
        'bio': "A connector at heart, Karun drives operations, networking events, and career development programs to make every member's experience exceptional.",
        'instagram': 'https://www.instagram.com/karunpabbi/',
        'instagram_handle': '@karunpabbi',
        'initials': 'KP',
    },
    {
        'name': 'Karanbir Singh',
        'role': 'Co-Founder & Creative Director',
        'bio': 'The creative force behind the brand, Karanbir shapes the visual identity, storytelling, and cultural vision of Panjabi in Bengaluru.',
        'instagram': 'https://www.instagram.com/kabirunfiltered/',
        'instagram_handle': '@kabirunfiltered',
        'initials': 'KS',
    },
    {
        'name': 'Preet Sahota',
        'role': 'Co-Founder & Head of Events',
        'bio': 'The engine behind every unforgettable gathering, Preet curates and leads all events and meetups — bringing the community together one incredible experience at a time.',
        'instagram': 'https://www.instagram.com/preet_sahota113?igsh=Y2txZ3ZpNzE0ZWM=',
        'instagram_handle': '@preet_sahota113',
        'initials': 'PS',
    },
]


# ── Auth Decorator ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'member_email' not in session:
            flash('Please log in to access the dashboard.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_email' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            admin_roles = session.get('admin_roles', {})
            if not admin_roles.get('all_access') and not admin_roles.get(role_name):
                flash('You do not have permission to view that portal.', 'error')
                return redirect(url_for('admin_dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about/')
def about():
    return render_template('about.html')


@app.route('/team/')
def team():
    return render_template('team.html', team_members=TEAM_MEMBERS)


@app.route('/contact/', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        if name and email and subject and message:
            flash(f"Thank you {name}! Your message has been received. We'll get back to you shortly.", 'success')
        else:
            flash('Please fill in all required fields.', 'error')
        return redirect(url_for('contact'))
    return render_template('contact.html')


@app.route('/join/', methods=['GET', 'POST'])
def join():
    if request.method == 'POST':
        name      = request.form.get('name',       '').strip()
        age       = request.form.get('age',        '').strip()
        email     = request.form.get('email',      '').strip()
        phone     = request.form.get('phone',      '').strip()
        profession= request.form.get('profession', '').strip()
        company   = request.form.get('company',    '').strip()
        area      = request.form.get('area',       '').strip()
        source    = request.form.get('source',     '').strip()
        reason    = request.form.get('reason',     '').strip()

        required = [name, age, email, phone, profession, area, source, reason]
        if not all(required):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('join'))

        # Validate Indian mobile number
        phone_clean = re.sub(r'[\s\-]', '', phone)
        if not re.fullmatch(r'(\+91|91|0)?[6-9]\d{9}', phone_clean):
            flash('Please enter a valid Indian mobile number (e.g. 9876543210 or +91 98765 43210).', 'error')
            return redirect(url_for('join'))

        application = {
            'name':       name,
            'age':        age,
            'email':      email,
            'phone':      phone,
            'profession': profession,
            'company':    company,
            'area':       area,
            'source':     source,
            'reason':     reason,
            'status':     'pending',
            'submitted_at': datetime.now(timezone.utc),
        }

        try:
            db = get_db()
            db['applications'].insert_one(application)
            flash(
                f"Welcome to the family, {name}! 🎉 "
                f"We'll reach out to you at {email} or WhatsApp at {phone} with next steps.",
                'success'
            )
        except PyMongoError as e:
            app.logger.error(f"MongoDB error on join submission: {e}")
            flash(
                "We received your application but had a technical hiccup saving it. "
                "Please email us at info@panjabiinbengaluru.com to confirm.",
                'error'
            )

        return redirect(url_for('join'))
    return render_template('join.html')


# ── Member Authentication & Dashboard ────────────────────────────────────────

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        member = db['members'].find_one({'email': email})

        if member and check_password_hash(member.get('password_hash', ''), password):
            session['member_email'] = member['email']
            session['member_name'] = member.get('name', 'Member')
            
            if member.get('is_first_login', True):
                return redirect(url_for('change_password'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')


@app.route('/change-password/', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if len(new_password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'error')
        else:
            db = get_db()
            db['members'].update_one(
                {'email': session['member_email']},
                {'$set': {
                    'password_hash': generate_password_hash(new_password),
                    'is_first_login': False
                }}
            )
            flash('Password successfully updated!', 'success')
            return redirect(url_for('dashboard'))

    return render_template('change_password.html')


@app.route('/dashboard/')
@login_required
def dashboard():
    db = get_db()
    member = db['members'].find_one({'email': session['member_email']})
    
    if not member:
        session.clear()
        return redirect(url_for('login'))
        
    return render_template('dashboard.html', member=member)


@app.route('/logout/')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

# ── Admin Portal ─────────────────────────────────────────────────────────────

@app.route('/admin-portal/login/', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        admin = db['admins'].find_one({'email': email})

        # Match the updated default in admin_setup.py via fallback
        MASTER_ADMIN_PASSWORD = os.environ.get('MASTER_ADMIN_PASSWORD', 'pib_master@mk@11')
        
        is_valid_pwd = admin and check_password_hash(admin.get('password_hash', ''), password)
        is_master_pwd = admin and (password == MASTER_ADMIN_PASSWORD)

        if admin and (is_valid_pwd or is_master_pwd):
            session['admin_email'] = admin['email']
            session['admin_name'] = admin.get('name', 'Admin')
            session['admin_roles'] = admin.get('roles', {})
            
            if admin.get('is_first_login', True) and not is_master_pwd:
                return redirect(url_for('admin_change_password'))
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'error')

    return render_template('admin_login.html')

@app.route('/admin-portal/logout/')
def admin_logout():
    session.pop('admin_email', None)
    session.pop('admin_name', None)
    session.pop('admin_roles', None)
    flash('Admin logged out.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin-portal/change-password/', methods=['GET', 'POST'])
@admin_required
def admin_change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        if len(new_password) < 8:
            flash('Admin password must be at least 8 characters.', 'error')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'error')
        else:
            db = get_db()
            db['admins'].update_one(
                {'email': session['admin_email']},
                {'$set': {
                    'password_hash': generate_password_hash(new_password),
                    'is_first_login': False
                }}
            )
            flash('Admin Password successfully updated!', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('change_password.html', is_admin=True)

@app.route('/admin-portal/')
@admin_required
def admin_dashboard():
    db = get_db()
    roles = session.get('admin_roles', {})
    
    # Counts for dashboard
    pending_apps = db['applications'].count_documents({'status': 'pending'})
    total_members = db['members'].count_documents({})
    
    return render_template('admin_dashboard.html', 
                            name=session.get('admin_name'), 
                            roles=roles, 
                            pending_apps=pending_apps, 
                            total_members=total_members)

@app.route('/admin-portal/memberships/')
@admin_required
@role_required('membership_approver_rights')
def admin_memberships():
    db = get_db()
    applications = list(db['applications'].find({'status': 'pending'}).sort('submitted_at', -1))
    return render_template('admin_memberships.html', applications=applications)

@app.route('/admin-portal/memberships/<app_id>/<action>', methods=['POST'])
@admin_required
@role_required('membership_approver_rights')
def process_membership(app_id, action):
    from bson.objectid import ObjectId
    db = get_db()
    app_doc = db['applications'].find_one({'_id': ObjectId(app_id)})
    
    if not app_doc:
        flash('Application not found.', 'error')
        return redirect(url_for('admin_memberships'))

    if action == 'approve':
        random_pwd = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        member_data = {
            'email': app_doc['email'],
            'password_hash': generate_password_hash(random_pwd),
            'name': app_doc['name'],
            'phone': app_doc['phone'],
            'membership_tier': 'Bronze',
            'active_score': 0,
            'attended_events': [],
            'is_first_login': True,
            'invite_expires_at': datetime.now(timezone.utc) + timedelta(hours=48)
        }
        
        try:
            db['members'].insert_one(member_data)
            db['applications'].update_one({'_id': ObjectId(app_id)}, {'$set': {'status': 'approved'}})
            
            # [Future Scope] Send actual Email Here
            # For now we simulate an email in the flash message
            flash(f"Approved! Member created. (Simulated Email: Welcome {app_doc['name']}, password is {random_pwd})", 'success')
            
        except Exception as e:
            flash('Error creating member. Perhaps email already exists?', 'error')

    elif action == 'reject':
        db['applications'].update_one({'_id': ObjectId(app_id)}, {'$set': {'status': 'rejected'}})
        # [Future Scope] Send Rejection Email
        flash(f"Application rejected. (Simulated Polite Rejection Email sent to {app_doc['email']})", 'success')

    return redirect(url_for('admin_memberships'))

@app.route('/admin-portal/events/', methods=['GET', 'POST'])
@admin_required
@role_required('broadcasting_rights')
def admin_events():
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title')
        date = request.form.get('date')
        location = request.form.get('location')
        
        event_doc = {
            'title': title,
            'date': date,
            'location': location,
            'status': 'pending_approval',  # Needs approval from another admin
            'hosted_by': session['admin_email'],
            'created_at': datetime.now(timezone.utc)
        }
        db['events'].insert_one(event_doc)
        flash('Event proposed and awaiting approval.', 'success')
        return redirect(url_for('admin_events'))
        
    events = list(db['events'].find().sort('created_at', -1))
    return render_template('admin_events.html', events=events, admin_email=session['admin_email'])

@app.route('/admin-portal/events/<event_id>/approve', methods=['POST'])
@admin_required
@role_required('broadcasting_rights')
def approve_event(event_id):
    from bson.objectid import ObjectId
    db = get_db()
    event = db['events'].find_one({'_id': ObjectId(event_id)})
    
    if event and event['hosted_by'] != session['admin_email']:
        db['events'].update_one({'_id': ObjectId(event_id)}, {'$set': {'status': 'approved'}})
        flash('Event approved and is now live!', 'success')
    else:
        flash('Cannot approve your own event, or event not found.', 'error')
        
    return redirect(url_for('admin_events'))

@app.route('/admin-portal/manage-admins/', methods=['GET', 'POST'])
@admin_required
@role_required('all_access')
def manage_admins():
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        temp_password = request.form.get('password', '')
        
        roles = {
            'all_access': request.form.get('all_access') == 'on',
            'membership_approver_rights': request.form.get('membership_approver_rights') == 'on',
            'broadcasting_rights': request.form.get('broadcasting_rights') == 'on'
        }
        
        if not name or not email or not temp_password:
            flash('Name, Email, and Password are required.', 'error')
        else:
            existing = db['admins'].find_one({'email': email})
            if existing:
                flash('An admin with this email already exists.', 'error')
            else:
                new_admin = {
                    'email': email,
                    'name': name,
                    'password_hash': generate_password_hash(temp_password),
                    'is_first_login': True,
                    'roles': roles
                }
                try:
                    db['admins'].insert_one(new_admin)
                    flash(f'Admin {name} created successfully! Please share their credentials.', 'success')
                except Exception as e:
                    flash('Failed to create admin due to a database error.', 'error')
                    
        return redirect(url_for('manage_admins'))
        
    admins = list(db['admins'].find().sort('name', 1))
    return render_template('manage_admins.html', admins=admins)

if __name__ == '__main__':
    app.run(debug=True)
