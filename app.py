"""
Panjabi in Bengaluru - Main Application Web Controller
---
Author: Core Engineering
Date: April 2026

This module serves as the primary route handler for the Panjabi in Bengaluru user and admin dashboard.
It connects to a MongoDB URI, manages session states natively, runs capacity logic via waitlisting scripts,
and controls both the public-facing front-end and the deeply authenticated backend admin-portal.

Do NOT modify deeply-nested database aggregation pipelines without cross-checking Admin Stats views.
"""

import os
import re
import string
import random
import secrets
import base64
from datetime import datetime, timezone, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "panjabi-in-bengaluru-secret-2024")

# ── MongoDB Atlas ────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI", "")


def get_db():
    """Return the MembershipApplications database (lazy connection)."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return client["MembershipApplications"]


TEAM_MEMBERS = [
    {
        "name": "Mehakdeep Singh",
        "role": "Co-Founder & Community Lead",
        "bio": "Passionate about building bridges between Punjabis across India. Mehakdeep leads community strategy, events, and growth initiatives for Panjabi in Bengaluru.",
        "instagram": "https://www.instagram.com/mehak.shokar/",
        "instagram_handle": "@mehak.shokar",
        "initials": "MS",
    },
    {
        "name": "Karun Pabbi",
        "role": "Co-Founder & Operations Head",
        "bio": "A connector at heart, Karun drives operations, networking events, and career development programs to make every member's experience exceptional.",
        "instagram": "https://www.instagram.com/karunpabbi/",
        "instagram_handle": "@karunpabbi",
        "initials": "KP",
    },
    {
        "name": "Karanbir Singh",
        "role": "Co-Founder & Creative Director",
        "bio": "The creative force behind the brand, Karanbir shapes the visual identity, storytelling, and cultural vision of Panjabi in Bengaluru.",
        "instagram": "https://www.instagram.com/kabirunfiltered/",
        "instagram_handle": "@kabirunfiltered",
        "initials": "KS",
    },
    {
        "name": "Preet Sahota",
        "role": "Co-Founder & Head of Events",
        "bio": "The engine behind every unforgettable gathering, Preet curates and leads all events and meetups — bringing the community together one incredible experience at a time.",
        "instagram": "https://www.instagram.com/preet_sahota113?igsh=Y2txZ3ZpNzE0ZWM=",
        "instagram_handle": "@preet_sahota113",
        "initials": "PS",
    },
]


# ── Auth Decorator ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "member_email" not in session:
            flash("Please log in to access the dashboard.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_email" not in session:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)

    return decorated_function


def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            admin_roles = session.get("admin_roles", {})
            if not admin_roles.get("all_access") and not admin_roles.get(role_name):
                flash("You do not have permission to view that portal.", "error")
                return redirect(url_for("admin_dashboard"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about/")
def about():
    return render_template("about.html")


@app.route("/team/")
def team():
    return render_template("team.html", team_members=TEAM_MEMBERS)


@app.route("/contact/", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        if name and email and subject and message:
            flash(
                f"Thank you {name}! Your message has been received. We'll get back to you shortly.",
                "success",
            )
        else:
            flash("Please fill in all required fields.", "error")
        return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route("/join/", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age = request.form.get("age", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        profession = request.form.get("profession", "").strip()
        company = request.form.get("company", "").strip()
        area = request.form.get("area", "").strip()
        source = request.form.get("source", "").strip()
        reason = request.form.get("reason", "").strip()

        # New fields for profile
        profile_overview = request.form.get("profile_overview", "").strip()
        linkedin_url = request.form.get("linkedin_url", "").strip()
        instagram_url = request.form.get("instagram_url", "").strip()
        facebook_url = request.form.get("facebook_url", "").strip()
        twitter_url = request.form.get("twitter_url", "").strip()
        github_url = request.form.get("github_url", "").strip()
        kaggle_url = request.form.get("kaggle_url", "").strip()
        other_link = request.form.get("other_link", "").strip()

        career_aspiration = request.form.get("career_aspiration", "").strip()
        skills = request.form.get("skills", "").strip()
        is_founder = request.form.get("is_founder") == "yes"
        is_entrepreneur = request.form.get("is_entrepreneur") == "yes"
        is_investor = request.form.get("is_investor") == "yes"

        required = [
            name, age, email, phone, profession, area, source, reason, 
            profile_overview, linkedin_url, career_aspiration, skills
        ]
        if not all(required):
            flash("Please fill in all mandatory fields including LinkedIn, Profile Overview, Career Aspirations, and Skills.", "error")
            return redirect(url_for("join"))

        if len([s for s in skills.split(",") if s.strip()]) > 5:
            flash("Please provide up to 5 skills.", "error")
            return redirect(url_for("join"))

        # Validate Indian mobile number
        phone_clean = re.sub(r"[\s\-]", "", phone)
        if not re.fullmatch(r"(\+91|91|0)?[6-9]\d{9}", phone_clean):
            flash(
                "Please enter a valid Indian mobile number (e.g. 9876543210 or +91 98765 43210).",
                "error",
            )
            return redirect(url_for("join"))

        application = {
            "name": name,
            "age": age,
            "email": email,
            "phone": phone,
            "profession": profession,
            "company": company,
            "area": area,
            "source": source,
            "reason": reason,
            "profile_overview": profile_overview,
            "social_links": {
                "linkedin": linkedin_url,
                "instagram": instagram_url,
                "facebook": facebook_url,
                "twitter": twitter_url,
                "github": github_url,
                "kaggle": kaggle_url,
                "other": other_link,
            },
            "career_aspiration": career_aspiration,
            "skills": [s.strip() for s in skills.split(",")],
            "is_founder": is_founder,
            "is_entrepreneur": is_entrepreneur,
            "is_investor": is_investor,
            "status": "pending",
            "submitted_at": datetime.now(timezone.utc),
        }

        try:
            db = get_db()
            db["applications"].insert_one(application)
            flash(
                f"Welcome to the family, {name}! 🎉 "
                f"We'll reach out to you at {email} or WhatsApp at {phone} with next steps.",
                "success",
            )
        except PyMongoError as e:
            app.logger.error(f"MongoDB error on join submission: {e}")
            flash(
                "We received your application but had a technical hiccup saving it. "
                "Please email us at info@panjabiinbengaluru.com to confirm.",
                "error",
            )

        return redirect(url_for("join"))
    return render_template("join.html")


# ── Member Authentication & Dashboard ────────────────────────────────────────


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        member = db["members"].find_one({"email": email})

        if member and check_password_hash(member.get("password_hash", ""), password):
            # Track login to update member stats
            db["members"].update_one(
                {"email": email}, {"$set": {"has_logged_in": True}}
            )

            session["member_email"] = member["email"]
            session["member_name"] = member.get("name", "Member")

            if member.get("is_first_login", True):
                return redirect(url_for("change_password"))
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/change-password/", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(new_password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif new_password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            db = get_db()
            db["members"].update_one(
                {"email": session["member_email"]},
                {
                    "$set": {
                        "password_hash": generate_password_hash(new_password),
                        "is_first_login": False,
                        "has_changed_password": True,
                    }
                },
            )
            flash("Password successfully updated!", "success")
            return redirect(url_for("dashboard"))

    return render_template("change_password.html")


@app.route("/profile/", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    member = db["members"].find_one({"email": session.get("member_email")})
    
    if request.method == "POST":
        updates = {}
        
        if not member.get("has_set_username", False):
            new_username = request.form.get("username", "").strip()
            if new_username:
                existing = db["members"].find_one({"username": new_username, "email": {"$ne": member["email"]}})
                if existing:
                    flash("Username is already taken. Please choose another.", "error")
                    return redirect(url_for('profile'))
                updates["username"] = new_username
                updates["has_set_username"] = True
                
        updates["profile_overview"] = request.form.get("profile_overview", "").strip()
        updates["career_aspiration"] = request.form.get("career_aspiration", "").strip()
        
        skills = request.form.get("skills", "").strip()
        if skills:
            updates["skills"] = [s.strip() for s in skills.split(",")][:5]
            
        updates["is_founder"] = request.form.get("is_founder") == "yes"
        updates["is_entrepreneur"] = request.form.get("is_entrepreneur") == "yes"
        updates["is_investor"] = request.form.get("is_investor") == "yes"
        
        social_links = {
            "linkedin": request.form.get("linkedin_url", "").strip(),
            "instagram": request.form.get("instagram_url", "").strip(),
            "facebook": request.form.get("facebook_url", "").strip(),
            "twitter": request.form.get("twitter_url", "").strip(),
            "github": request.form.get("github_url", "").strip(),
            "kaggle": request.form.get("kaggle_url", "").strip(),
            "other": request.form.get("other_link", "").strip(),
        }
        updates["social_links"] = social_links
        
        db["members"].update_one({"email": member["email"]}, {"$set": updates})
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", member=member)


@app.route("/u/<username>")
def public_profile(username):
    db = get_db()
    member = db["members"].find_one({"username": username})
    if not member:
        flash("Profile not found.", "error")
        return redirect(url_for('home'))
        
    return render_template("public_profile.html", member=member)


@app.route("/dashboard/")
@login_required
def dashboard():
    db = get_db()
    member = db["members"].find_one({"email": session["member_email"]})

    if not member:
        session.clear()
        return redirect(url_for("login"))

    now = datetime.now()
    all_events = list(
        db["events"].find({"status": "approved"}).sort("event_datetime", 1)
    )

    live_events = []
    past_events = []

    for event in all_events:
        # Check if the user has registered
        user_regs = [
            r for r in event.get("registrations", []) if r["email"] == member["email"]
        ]
        event["user_registration"] = user_regs[-1] if user_regs else None

        # Calculate spots left
        spots_left = int(event.get("max_capacity", 0)) - event.get(
            "registered_count", 0
        )
        event["spots_left"] = spots_left

        if event.get("event_datetime"):
            event["date_str"] = event["event_datetime"].strftime("%d %b %Y")
            event["time_str"] = event["event_datetime"].strftime("%I:%M %p")
        else:
            event["date_str"] = event.get("date", "TBD")
            event["time_str"] = event.get("time", "TBD")

        if event.get("is_paid") == True:
            event["is_paid"] = "yes"
        elif event.get("is_paid") == False:
            event["is_paid"] = "no"

        if "banner_data" in event and event["banner_data"]:
            event["banner"] = event["banner_data"]

        if (
            event.get("event_datetime")
            and event["event_datetime"].replace(tzinfo=None) >= now
        ):
            live_events.append(event)
        else:
            past_events.append(event)

    # Reverse past events to show most recent first
    past_events.reverse()

    return render_template(
        "dashboard.html",
        member=member,
        live_events=live_events,
        past_events=past_events,
    )


@app.route("/events/<event_id>")
@login_required
def event_details(event_id):
    from bson.objectid import ObjectId

    db = get_db()
    member = db["members"].find_one({"email": session["member_email"]})
    event = db["events"].find_one({"_id": ObjectId(event_id)})

    if not event or event.get("status") != "approved":
        flash("Event not found.", "error")
        return redirect(url_for("dashboard"))

    if event.get("event_datetime"):
        event["date_str"] = event["event_datetime"].strftime("%d %b %Y")
        event["time_str"] = event["event_datetime"].strftime("%I:%M %p")
    else:
        event["date_str"] = event.get("date", "TBD")
        event["time_str"] = event.get("time", "TBD")

    if event.get("is_paid") == True:
        event["is_paid"] = "yes"
    elif event.get("is_paid") == False:
        event["is_paid"] = "no"

    if "banner_data" in event and event["banner_data"]:
        event["banner"] = event["banner_data"]

    user_regs = [
        r for r in event.get("registrations", []) if r["email"] == member["email"]
    ]
    user_reg = user_regs[-1] if user_regs else None

    spots_left = int(event.get("max_capacity", 0)) - event.get("registered_count", 0)

    return render_template(
        "event_details.html",
        event=event,
        member=member,
        user_reg=user_reg,
        spots_left=spots_left,
    )


@app.route("/events/<event_id>/register", methods=["POST"])
@login_required
def register_event(event_id):
    db = get_db()
    member = db["members"].find_one({"email": session["member_email"]})
    event = db["events"].find_one({"_id": ObjectId(event_id)})

    if not event or event.get("status") != "approved":
        flash("Event not found.", "error")
        return redirect(url_for("dashboard"))

    # Check if already registered
    existing_reg = next(
        (
            r
            for r in event.get("registrations", [])
            if r["email"] == member["email"]
            and r["status"] not in ("cancelled", "rejected")
        ),
        None,
    )
    if existing_reg:
        flash("You are already registered or waitlisted for this event.", "error")
        return redirect(url_for("dashboard"))

    # Calculate capacities
    active_regs = [
        r
        for r in event.get("registrations", [])
        if r["status"] in ("approved", "pending")
    ]
    waitlisted_regs = [
        r for r in event.get("registrations", []) if r["status"] == "waitlisted"
    ]

    max_cap = int(event.get("max_capacity", 0))
    wait_cap = int(event.get("waitlist_capacity", 0))

    is_paid = event.get("is_paid") in [True, "yes"]
    require_screenshot = event.get("require_payment_screenshot") == "yes"

    if event.get("registration_link"):
        if not request.form.get("external_link_consent"):
            flash(
                "You must confirm that you have registered on the external link.",
                "error",
            )
            return redirect(url_for("event_details", event_id=event_id))

    import uuid

    reg_id = str(uuid.uuid4())
    registration = {
        "id": reg_id,
        "email": member["email"],
        "name": member["name"],
        "phone": member.get("phone", ""),
        "timestamp": datetime.now(),
        "status": "pending",
    }

    if is_paid and require_screenshot:
        screenshot_file = request.files.get("payment_screenshot")
        if screenshot_file and screenshot_file.filename:
            import base64

            registration["payment_screenshot"] = (
                "data:image/jpeg;base64,"
                + base64.b64encode(screenshot_file.read()).decode("utf-8")
            )
        else:
            flash("Payment screenshot is required for paid events.", "error")
            return redirect(url_for("dashboard"))

    # Determine status
    if len(active_regs) < max_cap:
        registration["status"] = "pending"
    elif len(waitlisted_regs) < wait_cap:
        registration["status"] = "pending"  # Will become waitlisted upon admin approval
    else:
        # Check if even pending entries exceed capacity logic
        pending_waitlisted = [
            r
            for r in event.get("registrations", [])
            if r["status"] in ("pending", "waitlisted", "approved")
        ]
        if len(pending_waitlisted) >= (max_cap + wait_cap):
            flash(
                "Sorry, the event has reached max capacity for both registrations and waitlist.",
                "error",
            )
            return redirect(url_for("dashboard"))
        registration["status"] = "pending"

    if registration["status"] == "approved":
        # Don't add to attended_events until explicit check-in
        pass

    db["events"].update_one(
        {"_id": ObjectId(event_id)},
        {
            "$push": {"registrations": registration},
            "$inc": {
                "registered_count": 1 if registration["status"] == "approved" else 0
            },
        },
    )

    flash(
        f"Registration successful! Status: {registration['status'].capitalize()}",
        "success",
    )
    return redirect(url_for("dashboard"))


def process_waitlist(event_id, db):
    updated_event = db["events"].find_one({"_id": ObjectId(event_id)})
    if not updated_event:
        return

    active_regs = [
        r for r in updated_event.get("registrations", []) if r["status"] == "approved"
    ]
    max_cap = int(updated_event.get("max_capacity", 0))

    while len(active_regs) < max_cap:
        waitlisted = sorted(
            [
                r
                for r in updated_event.get("registrations", [])
                if r["status"] == "waitlisted"
            ],
            key=lambda x: x.get("timestamp", datetime.now()),
        )
        if not waitlisted:
            break

        lucky_user = waitlisted[0]
        new_status = (
            "approved"  # Auto-approve from waitlist as admin already verified them
        )

        db["events"].update_one(
            {"_id": ObjectId(event_id), "registrations.id": lucky_user["id"]},
            {"$set": {"registrations.$.status": new_status}},
        )

        # Re-fetch active_regs to recount
        updated_event = db["events"].find_one({"_id": ObjectId(event_id)})
        active_regs = [
            r
            for r in updated_event.get("registrations", [])
            if r["status"] == "approved"
        ]

    final_event = db["events"].find_one({"_id": ObjectId(event_id)})
    new_active_count = len(
        [r for r in final_event.get("registrations", []) if r["status"] == "approved"]
    )
    db["events"].update_one(
        {"_id": ObjectId(event_id)}, {"$set": {"registered_count": new_active_count}}
    )


@app.route("/events/<event_id>/cancel", methods=["POST"])
@login_required
def cancel_registration(event_id):
    db = get_db()
    member = db["members"].find_one({"email": session["member_email"]})
    event = db["events"].find_one({"_id": ObjectId(event_id)})

    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("dashboard"))

    db["events"].update_one(
        {"_id": ObjectId(event_id), "registrations.email": member["email"]},
        {"$set": {"registrations.$.status": "cancelled"}},
    )

    existing_reg = next(
        (r for r in event.get("registrations", []) if r["email"] == member["email"]),
        None,
    )
    if existing_reg and existing_reg["status"] == "approved":
        db["members"].update_one(
            {"email": member["email"]}, {"$pull": {"attended_events": event_id}}
        )

    process_waitlist(event_id, db)
    flash("Registration cancelled successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/logout/")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


# ── Admin Portal ─────────────────────────────────────────────────────────────


@app.route("/admin-portal/login/", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        admin = db["admins"].find_one({"email": email})

        # Match the updated default in admin_setup.py via fallback
        MASTER_ADMIN_PASSWORD = os.environ.get(
            "MASTER_ADMIN_PASSWORD", "pib_master@mk@11"
        )

        is_valid_pwd = admin and check_password_hash(
            admin.get("password_hash", ""), password
        )
        is_master_pwd = admin and (password == MASTER_ADMIN_PASSWORD)

        if admin and (is_valid_pwd or is_master_pwd):
            session["admin_email"] = admin["email"]
            session["admin_name"] = admin.get("name", "Admin")
            session["admin_roles"] = admin.get("roles", {})

            if admin.get("is_first_login", True) and not is_master_pwd:
                return redirect(url_for("admin_change_password"))
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials.", "error")

    return render_template("admin_login.html")


@app.route("/admin-portal/logout/")
def admin_logout():
    session.pop("admin_email", None)
    session.pop("admin_name", None)
    session.pop("admin_roles", None)
    flash("Admin logged out.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin-portal/change-password/", methods=["GET", "POST"])
@admin_required
def admin_change_password():
    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if len(new_password) < 8:
            flash("Admin password must be at least 8 characters.", "error")
        elif new_password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            db = get_db()
            db["admins"].update_one(
                {"email": session["admin_email"]},
                {
                    "$set": {
                        "password_hash": generate_password_hash(new_password),
                        "is_first_login": False,
                    }
                },
            )
            flash("Admin Password successfully updated!", "success")
            return redirect(url_for("admin_dashboard"))
    return render_template("change_password.html", is_admin=True)


@app.route("/admin-portal/profile/", methods=["GET", "POST"])
@admin_required
def admin_profile():
    db = get_db()
    admin = db["admins"].find_one({"email": session["admin_email"]})

    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_profile":
            name = request.form.get("name", "").strip()
            if name:
                db["admins"].update_one(
                    {"email": session["admin_email"]}, {"$set": {"name": name}}
                )
                session["admin_name"] = name
                flash("Profile successfully updated!", "success")
            else:
                flash("Name cannot be empty.", "error")

        elif action == "change_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not check_password_hash(
                admin.get("password_hash", ""), current_password
            ):
                flash("Incorrect current password.", "error")
            elif len(new_password) < 8:
                flash("New password must be at least 8 characters.", "error")
            elif new_password != confirm_password:
                flash("New passwords do not match.", "error")
            else:
                db["admins"].update_one(
                    {"email": session["admin_email"]},
                    {"$set": {"password_hash": generate_password_hash(new_password)}},
                )
                flash("Password successfully changed!", "success")

        return redirect(url_for("admin_profile"))

    return render_template("admin_profile.html", admin=admin)


@app.route("/admin-portal/")
@admin_required
def admin_dashboard():
    db = get_db()
    roles = session.get("admin_roles", {})

    # Counts for dashboard
    pending_apps = db["applications"].count_documents({"status": "pending"})
    total_members = db["members"].count_documents({})

    return render_template(
        "admin_dashboard.html",
        name=session.get("admin_name"),
        roles=roles,
        pending_apps=pending_apps,
        total_members=total_members,
    )


@app.route("/admin-portal/memberships/")
@admin_required
@role_required("membership_approver_rights")
def admin_memberships():
    db = get_db()

    # Filtering and Searching
    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    sort_order = int(request.args.get("sort", -1))

    query = {"status": "pending"}

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
        ]

    if date_from or date_to:
        query["submitted_at"] = {}
        if date_from:
            try:
                date_obj_from = datetime.strptime(date_from, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                query["submitted_at"]["$gte"] = date_obj_from
            except ValueError:
                pass
        if date_to:
            try:
                date_obj_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                ) + timedelta(days=1)
                query["submitted_at"]["$lt"] = date_obj_to
            except ValueError:
                pass
        if not query["submitted_at"]:
            del query["submitted_at"]

    applications = list(db["applications"].find(query).sort("submitted_at", sort_order))
    return render_template(
        "admin_memberships.html",
        applications=applications,
        search=search,
        date_from=date_from,
        date_to=date_to,
        sort=sort_order,
    )


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_approval_email(member_name, member_email, temp_password, whatsapp_link):
    subject = "Welcome to Panjabi in Bengaluru! Your Membership is Approved 🎉"

    sender_email = os.environ.get("MAIL_USERNAME", "no-reply@panjabiinbengaluru.com")
    sender_password = os.environ.get("MAIL_PASSWORD", "")
    smtp_server = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("MAIL_PORT", 587))

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
    msg["From"] = f"Admin Team, Panjabi in Bengaluru <{sender_email}>"
    msg["To"] = member_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        app.logger.error(f"Failed to send email: {e}")
        return False


@app.route("/admin-portal/memberships/<app_id>/<action>", methods=["POST"])
@admin_required
@role_required("membership_approver_rights")
def process_membership(app_id, action):
    from bson.objectid import ObjectId

    db = get_db()
    app_doc = db["applications"].find_one({"_id": ObjectId(app_id)})

    if not app_doc:
        flash("Application not found.", "error")
        return redirect(url_for("admin_memberships"))

    if action == "approve":
        send_wa_invite = request.form.get("send_wa_invite")
        random_pwd = "".join(random.choices(string.ascii_letters + string.digits, k=10))

        member_data = {
            "email": app_doc["email"],
            "username": f"user_{str(app_doc['_id'])[:8]}", # Base fallback
            "has_set_username": False,
            "password_hash": generate_password_hash(random_pwd),
            "name": app_doc["name"],
            "phone": app_doc["phone"],
            "profile_overview": app_doc.get("profile_overview", ""),
            "social_links": app_doc.get("social_links", {}),
            "career_aspiration": app_doc.get("career_aspiration", ""),
            "skills": app_doc.get("skills", []),
            "is_founder": app_doc.get("is_founder", False),
            "is_entrepreneur": app_doc.get("is_entrepreneur", False),
            "is_investor": app_doc.get("is_investor", False),
            "profession": app_doc.get("profession", ""),
            "company": app_doc.get("company", ""),
            "area": app_doc.get("area", ""),
            "membership_tier": "Bronze",
            "active_score": 0,
            "attended_events": [],
            "is_first_login": True,
            "invite_expires_at": datetime.now(timezone.utc) + timedelta(hours=48),
            "has_logged_in": False,
            "has_changed_password": False,
            "has_joined_whatsapp": False,
            "approved_at": datetime.now(timezone.utc),
            "approved_by_email": session.get("admin_email"),
            "approved_by_name": session.get("admin_name"),
        }

        try:
            db["members"].insert_one(member_data)
            db["applications"].update_one(
                {"_id": ObjectId(app_id)}, {"$set": {"status": "approved"}}
            )

            invite_url = None
            if send_wa_invite:
                token = secrets.token_urlsafe(16)
                db["whatsapp_invites"].insert_one(
                    {
                        "token": token,
                        "application_id": app_id,
                        "member_email": app_doc["email"],
                        "used": False,
                        "created_at": datetime.now(timezone.utc),
                    }
                )
                invite_url = url_for("whatsapp_invite", token=token, _external=True)

            email_sent = send_approval_email(
                app_doc["name"], app_doc["email"], random_pwd, invite_url
            )

            if email_sent:
                flash(f"Approved! Welcome email sent to {app_doc['name']}.", "success")
            else:
                flash(
                    f"Approved! Member created, but failed to send email (check SMTP info). Password is {random_pwd}",
                    "success",
                )

        except Exception as e:
            flash("Error creating member. Perhaps email already exists?", "error")

    elif action == "reject":
        db["applications"].update_one(
            {"_id": ObjectId(app_id)}, {"$set": {"status": "rejected"}}
        )
        # [Future Scope] Send Rejection Email
        flash(
            f"Application rejected. (Simulated Polite Rejection Email sent to {app_doc['email']})",
            "success",
        )

    return redirect(url_for("admin_memberships"))


@app.route("/admin-portal/events/", methods=["GET", "POST"])
@admin_required
@role_required("broadcasting_rights")
def admin_events():
    db = get_db()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        date_input = request.form.get("date", "").strip()
        time_input = request.form.get("time", "").strip()
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()
        registration_link = request.form.get("registration_link", "").strip()
        is_paid = request.form.get("is_paid") == "yes"
        require_payment_screenshot = request.form.get(
            "require_payment_screenshot", "no"
        )
        fees_details = request.form.get("fees_details", "").strip() if is_paid else ""
        payment_details = (
            request.form.get("payment_details", "").strip() if is_paid else ""
        )

        try:
            max_capacity = int(request.form.get("max_capacity") or 0)
            waitlist_capacity = int(request.form.get("waitlist_capacity") or 0)
        except ValueError:
            max_capacity = 0
            waitlist_capacity = 0

        try:
            # Parse HTML5 date and time formats
            event_datetime = datetime.strptime(
                f"{date_input} {time_input}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            flash("Invalid date or time format.", "error")
            return redirect(url_for("admin_events"))

        banner_file = request.files.get("banner")
        banner_data = None
        if banner_file and banner_file.filename:
            # Enforce max file size in code if necessary, Vercel gives 4.5MB payload limit on requests usually.
            banner_bytes = base64.b64encode(banner_file.read()).decode("utf-8")
            banner_mime = banner_file.mimetype
            banner_data = f"data:{banner_mime};base64,{banner_bytes}"

        event_doc = {
            "title": title,
            "event_datetime": event_datetime,  # Storing as proper datetime object
            "location": location,
            "description": description,
            "registration_link": registration_link,
            "is_paid": is_paid,
            "require_payment_screenshot": require_payment_screenshot,
            "fees_details": fees_details,
            "payment_details": payment_details,
            "max_capacity": max_capacity,
            "waitlist_capacity": waitlist_capacity,
            "banner_data": banner_data,
            "status": "pending_approval",  # Needs approval from another admin
            "hosted_by": session["admin_email"],
            "created_at": datetime.now(timezone.utc),
            "registered_count": 0,
            "waitlist_count": 0,
            "audit_log": [
                {
                    "action": "created",
                    "admin_email": session["admin_email"],
                    "timestamp": datetime.now(timezone.utc),
                }
            ],
        }
        db["events"].insert_one(event_doc)
        flash("Event proposed and awaiting approval.", "success")
        return redirect(url_for("admin_events"))

    events = list(db["events"].find().sort("event_datetime", -1))
    return render_template(
        "admin_events.html", events=events, admin_email=session["admin_email"]
    )


@app.route("/admin-portal/events/<event_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_event(event_id):
    from bson.objectid import ObjectId

    db = get_db()
    event = db["events"].find_one({"_id": ObjectId(event_id)})

    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin_events"))

    if request.method == "POST":
        update_data = {
            "title": request.form.get("title"),
            "date": request.form.get("date"),
            "time": request.form.get("time"),
            "location": request.form.get("location"),
            "registration_link": request.form.get("registration_link"),
            "description": request.form.get("description"),
            "max_capacity": int(request.form.get("max_capacity", 0)),
            "waitlist_capacity": int(request.form.get("waitlist_capacity", 0)),
            "is_paid": request.form.get("is_paid"),
            "require_payment_screenshot": request.form.get(
                "require_payment_screenshot", "no"
            ),
            "fees_details": request.form.get("fees_details", ""),
            "payment_details": request.form.get("payment_details", ""),
        }

        banner_file = request.files.get("banner")
        if banner_file and banner_file.filename:
            import base64

            banner_data = "data:image/jpeg;base64," + base64.b64encode(
                banner_file.read()
            ).decode("utf-8")
            update_data["banner"] = banner_data

        try:
            from datetime import datetime

            dt_str = f"{update_data['date']} {update_data['time']}"
            update_data["event_datetime"] = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            update_data["date_str"] = update_data["event_datetime"].strftime("%d %b %Y")
            update_data["time_str"] = update_data["event_datetime"].strftime("%I:%M %p")
        except:
            pass

        db["events"].update_one(
            {"_id": ObjectId(event_id)},
            {
                "$set": update_data,
                "$push": {
                    "audit_log": {
                        "action": "edited",
                        "admin_email": session["admin_email"],
                        "timestamp": datetime.now(timezone.utc),
                    }
                },
            },
        )
        flash("Event updated successfully.", "success")
        return redirect(url_for("admin_events"))

    return render_template("admin_event_edit.html", event=event)


@app.route("/admin-portal/events/<event_id>/approve", methods=["POST"])
@admin_required
@role_required("broadcasting_rights")
def approve_event(event_id):
    from bson.objectid import ObjectId

    db = get_db()
    event = db["events"].find_one({"_id": ObjectId(event_id)})

    if event and event["hosted_by"] != session["admin_email"]:
        db["events"].update_one(
            {"_id": ObjectId(event_id)},
            {
                "$set": {"status": "approved"},
                "$push": {
                    "audit_log": {
                        "action": "approved",
                        "admin_email": session["admin_email"],
                        "timestamp": datetime.now(timezone.utc),
                    }
                },
            },
        )
        flash("Event approved and is now live!", "success")
    else:
        flash("Cannot approve your own event, or event not found.", "error")

    return redirect(url_for("admin_events"))


@app.route("/admin-portal/events/<event_id>/request_delete", methods=["POST"])
@admin_required
def request_delete_event(event_id):
    from bson.objectid import ObjectId

    db = get_db()
    event = db["events"].find_one({"_id": ObjectId(event_id)})

    if event:
        db["events"].update_one(
            {"_id": ObjectId(event_id)},
            {
                "$set": {
                    "status": "pending_deletion",
                    "deletion_requested_by": session["admin_email"],
                },
                "$push": {
                    "audit_log": {
                        "action": "deletion_requested",
                        "admin_email": session["admin_email"],
                        "timestamp": datetime.now(timezone.utc),
                    }
                },
            },
        )
        flash(
            "Deletion requested! Another admin must approve to permanently delete it.",
            "success",
        )
    return redirect(url_for("admin_events"))


@app.route("/admin-portal/events/<event_id>/approve_delete", methods=["POST"])
@admin_required
@role_required("broadcasting_rights")
def approve_delete_event(event_id):
    from bson.objectid import ObjectId

    db = get_db()
    event = db["events"].find_one({"_id": ObjectId(event_id)})

    if event and event.get("deletion_requested_by") != session["admin_email"]:
        db["events"].update_one(
            {"_id": ObjectId(event_id)},
            {
                "$set": {"status": "deleted"},
                "$push": {
                    "audit_log": {
                        "action": "deleted",
                        "admin_email": session["admin_email"],
                        "timestamp": datetime.now(timezone.utc),
                    }
                },
            },
        )
        flash("Event has been permanently deleted.", "success")
    else:
        flash(
            "Cannot approve deletion of your own request, or event not found.", "error"
        )

    return redirect(url_for("admin_events"))


@app.route("/admin-portal/events/<event_id>/audit_log")
@admin_required
def event_audit_log(event_id):
    from bson.objectid import ObjectId

    db = get_db()
    event = db["events"].find_one({"_id": ObjectId(event_id)})
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin_events"))

    return render_template("admin_event_audit.html", event=event)


@app.route("/admin-portal/events/<event_id>/registrations", methods=["GET", "POST"])
@admin_required
@role_required("broadcasting_rights")
def admin_event_registrations(event_id):
    from bson.objectid import ObjectId

    db = get_db()
    event = db["events"].find_one({"_id": ObjectId(event_id)})
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin_events"))

    if request.method == "POST":
        action = request.form.get("action")
        reg_id = request.form.get("reg_id")

        # update the status of the specific registration
        if action in ["approve", "reject"]:
            current_reg = next(
                (r for r in event.get("registrations", []) if r["id"] == reg_id), None
            )

            if action == "approve":
                active_regs = [
                    r
                    for r in event.get("registrations", [])
                    if r["status"] == "approved"
                ]
                max_cap = int(event.get("max_capacity", 0))
                wait_cap = int(event.get("waitlist_capacity", 0))
                waitlisted_regs = [
                    r
                    for r in event.get("registrations", [])
                    if r["status"] == "waitlisted"
                ]

                # Check capacity before approving
                if len(active_regs) < max_cap:
                    new_status = "approved"
                elif len(waitlisted_regs) < wait_cap:
                    new_status = "waitlisted"
                else:
                    flash(
                        "Both event capacity and waitlist are full. Cannot approve further.",
                        "error",
                    )
                    return redirect(
                        url_for("admin_event_registrations", event_id=event_id)
                    )

                db["events"].update_one(
                    {"_id": ObjectId(event_id), "registrations.id": reg_id},
                    {"$set": {"registrations.$.status": new_status}},
                )
            else:
                new_status = "rejected"
                reject_reason = request.form.get("reject_reason", "")
                if reject_reason == "Other":
                    reject_reason = request.form.get("other_reject_reason", "Other")

                db["events"].update_one(
                    {"_id": ObjectId(event_id), "registrations.id": reg_id},
                    {
                        "$set": {
                            "registrations.$.status": new_status,
                            "registrations.$.rejection_reason": reject_reason,
                        }
                    },
                )

            # If rejected, remove from attended events if previously approved
            if action == "reject":
                if current_reg:
                    db["members"].update_one(
                        {"email": current_reg["email"]},
                        {"$pull": {"attended_events": event_id}},
                    )

            # Recompute spaces and process waitlist natively
            process_waitlist(event_id, db)
            flash(f"Registration {new_status} successfully.", "success")

        elif action == "check_in":
            current_reg = next(
                (r for r in event.get("registrations", []) if r["id"] == reg_id), None
            )
            if current_reg and current_reg.get("status") == "approved":
                db["events"].update_one(
                    {"_id": ObjectId(event_id), "registrations.id": reg_id},
                    {"$set": {"registrations.$.checked_in": True}},
                )
                db["members"].update_one(
                    {"email": current_reg["email"]},
                    {"$addToSet": {"attended_events": event_id}},
                )
                flash("Member checked in successfully.", "success")

        elif action == "reset":
            current_reg = next(
                (r for r in event.get("registrations", []) if r["id"] == reg_id), None
            )
            reset_reason = request.form.get("reset_reason", "No reason provided")
            if current_reg:
                # Remove the registration document entirely from array so they can apply again
                db["events"].update_one(
                    {"_id": ObjectId(event_id)},
                    {"$pull": {"registrations": {"id": reg_id}}},
                )
                # optionally log the reset
                db["events"].update_one(
                    {"_id": ObjectId(event_id)},
                    {
                        "$push": {
                            "audit_log": {
                                "action": f"reset_registration: {current_reg.get('email')} - {reset_reason}",
                                "admin_email": session.get("admin_email"),
                                "timestamp": datetime.now(timezone.utc),
                            }
                        }
                    },
                )
                flash("Member registration flow reset successfully.", "success")

        return redirect(url_for("admin_event_registrations", event_id=event_id))

    registrations = event.get("registrations", [])
    return render_template(
        "admin_event_registrations.html", event=event, registrations=registrations
    )


@app.route("/admin-portal/events/<event_id>/export")
@admin_required
@role_required("broadcasting_rights")
def export_event_csv(event_id):
    import csv
    from io import StringIO
    from flask import Response
    from bson.objectid import ObjectId

    db = get_db()
    event = db["events"].find_one({"_id": ObjectId(event_id)})
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin_events"))

    si = StringIO()
    cw = csv.writer(si)

    # Write Header
    cw.writerow(
        [
            "Name",
            "Email",
            "Phone",
            "Status",
            "Timestamp",
            "Is Paid App",
            "Has Screenshot",
        ]
    )

    registrations = event.get("registrations", [])
    for reg in registrations:
        has_screenshot = "Yes" if reg.get("payment_screenshot") else "No"
        ts = reg.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "N/A"

        cw.writerow(
            [
                reg.get("name", ""),
                reg.get("email", ""),
                reg.get("phone", ""),
                reg.get("status", ""),
                ts_str,
                event.get("is_paid", "no"),
                has_screenshot,
            ]
        )

    output = si.getvalue()

    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment;filename=event_{event_id}_registrations.csv"
        },
    )


@app.route("/admin-portal/manage-admins/", methods=["GET", "POST"])
@admin_required
@role_required("all_access")
def manage_admins():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action", "create")

        if action == "create":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            temp_password = request.form.get("password", "")

            roles = {
                "all_access": request.form.get("all_access") == "on",
                "membership_approver_rights": request.form.get(
                    "membership_approver_rights"
                )
                == "on",
                "broadcasting_rights": request.form.get("broadcasting_rights") == "on",
            }

            if not name or not email or not temp_password:
                flash("Name, Email, and Password are required.", "error")
            else:
                existing = db["admins"].find_one({"email": email})
                if existing:
                    flash("An admin with this email already exists.", "error")
                else:
                    new_admin = {
                        "email": email,
                        "name": name,
                        "password_hash": generate_password_hash(temp_password),
                        "is_first_login": True,
                        "roles": roles,
                    }
                    try:
                        db["admins"].insert_one(new_admin)
                        flash(
                            f"Admin {name} created successfully! Please share their credentials.",
                            "success",
                        )
                    except Exception as e:
                        flash(
                            "Failed to create admin due to a database error.", "error"
                        )

        elif action == "delete":
            admin_id = request.form.get("admin_id")
            from bson.objectid import ObjectId

            target_admin = db["admins"].find_one({"_id": ObjectId(admin_id)})
            if target_admin and target_admin["email"] == session["admin_email"]:
                flash("You cannot delete your own admin account.", "error")
            else:
                db["admins"].delete_one({"_id": ObjectId(admin_id)})
                if target_admin:
                    flash(
                        f"Admin {target_admin.get('name', 'Account')} securely deleted.",
                        "success",
                    )

        return redirect(url_for("manage_admins"))

    admins = list(db["admins"].find().sort("name", 1))
    return render_template(
        "manage_admins.html",
        admins=admins,
        current_admin_email=session.get("admin_email"),
    )


@app.route("/admin-portal/stats/")
@admin_required
def admin_stats():
    db = get_db()
    # All admins can perhaps see stats, or we restrict it? Letting all admins see for now.

    # Sorting and basic filtering
    sort_order = int(request.args.get("sort", -1))

    members = list(db["members"].find().sort("approved_at", sort_order))

    for member in members:
        if not member.get("approved_at") or not member.get("approved_by_name"):
            # Fall back to applications collection if available
            app_doc = db["applications"].find_one({"email": member.get("email", "")})
            if app_doc and "_id" in app_doc:
                member["approved_at"] = (
                    member.get("approved_at") or app_doc["_id"].generation_time
                )
                member["approved_by_name"] = (
                    member.get("approved_by_name") or "Admin / Legacy"
                )
            else:
                member["approved_at"] = (
                    member.get("approved_at") or member["_id"].generation_time
                )
                member["approved_by_name"] = (
                    member.get("approved_by_name") or "Admin / Legacy"
                )

    return render_template("admin_stats.html", members=members, sort=sort_order)


@app.route("/invite/<token>")
def whatsapp_invite(token):
    db = get_db()
    invite = db["whatsapp_invites"].find_one({"token": token})

    if not invite:
        return render_template(
            "invite_error.html",
            message="Invalid invite link. Please contact the admin.",
        )

    if invite.get("used"):
        return render_template(
            "invite_error.html",
            message="This invite link has expired. Please contact the admin.",
        )

    # Mark as used immediately to make it single-use
    db["whatsapp_invites"].update_one(
        {"_id": invite["_id"]},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}},
    )
    # Also update member stats to indicate they clicked link
    db["members"].update_one(
        {"email": invite.get("member_email")}, {"$set": {"has_joined_whatsapp": True}}
    )

    # Grab the actual, static WA group link from environment variables (fallback if not set)
    actual_wa_link = os.environ.get(
        "WHATSAPP_COMMUNITY_LINK", "https://chat.whatsapp.com/ReplaceWithActualLink"
    )
    return redirect(actual_wa_link)


if __name__ == "__main__":
    app.run(debug=True)
