import os
import re
import string
import random
import secrets
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

@app.route('/admin-portal/profile/', methods=['GET', 'POST'])
@admin_required
def admin_profile():
    db = get_db()
    admin = db['admins'].find_one({'email': session['admin_email']})
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            if name:
                db['admins'].update_one(
                    {'email': session['admin_email']},
                    {'$set': {'name': name}}
                )
                session['admin_name'] = name
                flash('Profile successfully updated!', 'success')
            else:
                flash('Name cannot be empty.', 'error')
                
        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not check_password_hash(admin.get('password_hash', ''), current_password):
                flash('Incorrect current password.', 'error')
            elif len(new_password) < 8:
                flash('New password must be at least 8 characters.', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'error')
            else:
                db['admins'].update_one(
                    {'email': session['admin_email']},
                    {'$set': {'password_hash': generate_password_hash(new_password)}}
                )
                flash('Password successfully changed!', 'success')
                
        return redirect(url_for('admin_profile'))
        
    return render_template('admin_profile.html', admin=admin)

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
    
    # Filtering and Searching
    search = request.args.get('search', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    sort_order = int(request.args.get('sort', -1))
    
    query = {'status': 'pending'}
    
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
            {'phone': {'$regex': search, '$options': 'i'}}
        ]
        
    if date_from or date_to:
        query['submitted_at'] = {}
        if date_from:
            try:
                date_obj_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                query['submitted_at']['$gte'] = date_obj_from
            except ValueError:
                pass
        if date_to:
            try:
                date_obj_to = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
                query['submitted_at']['$lt'] = date_obj_to
            except ValueError:
                pass
        if not query['submitted_at']:
            del query['submitted_at']

    applications = list(db['applications'].find(query).sort('submitted_at', sort_order))
    return render_template('admin_memberships.html', applications=applications,
                           search=search, date_from=date_from, date_to=date_to, sort=sort_order)

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_approval_email(member_name, member_email, temp_password, whatsapp_link):
    subject = "Welcome to Panjabi in Bengaluru! Your Membership is Approved 🎉"
    
    sender_email = os.environ.get('MAIL_USERNAME', 'no-reply@panjabiinbengaluru.com')
    sender_password = os.environ.get('MAIL_PASSWORD', '')
    smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('MAIL_PORT', 587))
    
    body = f"""Greetings {member_name},

We are absolutely thrilled to share that your membership application has been approved! Welcome to the Panjabi in Bengaluru family.

Whether you are looking to celebrate our shared heritage, build new professional connections, or simply find a vibrant slice of Punjab right here in Namma Bengaluru, you have come to the exact right place. We cannot wait to see the energy and ideas you will bring to our community.

To get you started, here are your official access details for the community portal:

Your Login Credentials
Please use the details below to log into your new account. For your security, you will be prompted to create a new, permanent password immediately upon your first login.

Login Portal: https://www.panjabiinbengaluru.com/login
Registered Email: {member_email}
Password: {temp_password}

Join the Conversation on WhatsApp
Our community is highly active on WhatsApp, where we share real-time updates, event details, and everyday conversations.
"""

    if whatsapp_link:
        body += f"""
Click the link below to join our official WhatsApp Community Group:
👉 {whatsapp_link}

Note: This is a personalized, single-use invite link generated specifically for you. It will automatically expire once you have joined the group or within 48 hours, so please be sure to hop in soon!
"""
    else:
        body += "\n(WhatsApp invite link will be shared with you shortly by the Admin team)\n"

    body += """
If you have any trouble logging in or accessing the group, simply reply to this email, and our team will get it sorted out for you right away.

Once again, welcome to the community. We look forward to seeing you at our next meetup!

Warm regards,

Admin Team, 
Panjabi in Bengaluru
https://www.panjabiinbengaluru.com
"""

    if not sender_password:
        return False  # Email not configured
        
    msg = MIMEMultipart()
    msg['From'] = f"Admin Team, Panjabi in Bengaluru <{sender_email}>"
    msg['To'] = member_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

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
        send_wa_invite = request.form.get('send_wa_invite')
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
            
            invite_url = None
            if send_wa_invite:
                token = secrets.token_urlsafe(16)
                db['whatsapp_invites'].insert_one({
                    'token': token,
                    'application_id': app_id,
                    'member_email': app_doc['email'],
                    'used': False,
                    'created_at': datetime.now(timezone.utc)
                })
                invite_url = url_for('whatsapp_invite', token=token, _external=True)

            email_sent = send_approval_email(app_doc['name'], app_doc['email'], random_pwd, invite_url)
            
            if email_sent:
                flash(f"Approved! Welcome email sent to {app_doc['name']}.", 'success')
            else:
                flash(f"Approved! Member created, but failed to send email (check SMTP info). Password is {random_pwd}", 'success')
            
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

@app.route('/invite/<token>')
def whatsapp_invite(token):
    db = get_db()
    invite = db['whatsapp_invites'].find_one({'token': token})
    
    if not invite:
        return render_template('invite_error.html', message="Invalid invite link. Please contact the admin.")
        
    if invite.get('used'):
        return render_template('invite_error.html', message="This invite link has expired. Please contact the admin.")
        
    # Mark as used immediately to make it single-use
    db['whatsapp_invites'].update_one(
        {'_id': invite['_id']}, 
        {'$set': {'used': True, 'used_at': datetime.now(timezone.utc)}}
    )
    
    # Grab the actual, static WA group link from environment variables (fallback if not set)
    actual_wa_link = os.environ.get('WHATSAPP_COMMUNITY_LINK', 'https://chat.whatsapp.com/ReplaceWithActualLink')
    return redirect(actual_wa_link)

if __name__ == '__main__':
    app.run(debug=True)
