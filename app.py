import os
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
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


if __name__ == '__main__':
    app.run(debug=True)
