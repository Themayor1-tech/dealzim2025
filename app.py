from flask import Flask, render_template, redirect, url_for, flash, request, session, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from models import db, User, Listing, Admin, CATEGORIES
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
load_dotenv()
import os 

app = Flask(__name__)
app.secret_key = 'dealzim-secret-key-change-later'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///dealzim.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# ── Email config ──
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access that page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()
    if not Admin.query.first():
        default_admin = Admin(
            username='admin',
            password=generate_password_hash('dealzim2025')
        )
        db.session.add(default_admin)
        db.session.commit()

# ── Admin decorator ──
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ══════════════════════════════════════
# PUBLIC ROUTES
# ══════════════════════════════════════

@app.route('/')
def home():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    query = Listing.query.filter_by(is_approved=True)

    if search:
        query = query.filter(
            Listing.title.ilike(f'%{search}%') |
            Listing.description.ilike(f'%{search}%') |
            Listing.location.ilike(f'%{search}%')
        )

    if category:
        query = query.filter_by(category=category)

    listings = query.order_by(Listing.date_posted.desc()).all()

    return render_template('home.html',
                           listings=listings,
                           categories=CATEGORIES,
                           search=search,
                           selected_category=category)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        username = request.form.get('username').lower().strip()
        whatsapp = request.form.get('whatsapp')
        location = request.form.get('location')
        password = request.form.get('password')
        role = request.form.get('role')
        email = request.form.get('email').lower().strip()

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('That username is already taken.', 'danger')
            return redirect(url_for('register'))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('That email is already registered.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(
            fullname=fullname,
            username=username,
            email=email,
            whatsapp=whatsapp,
            location=location,
            password=hashed_password,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()

        # Send verification email
        token = serializer.dumps(email, salt='email-verify')
        verify_url = url_for('verify_email', token=token, _external=True)

        # Always redirect immediately — never let email sending block the page
        try:
            msg = Message(
                subject='Verify your Dealzim account',
                recipients=[email]
            )
            msg.body = f"""Hi {fullname},

Welcome to Dealzim!

Click the link below to verify your email.
This link expires in 6 hours.

{verify_url}

If you did not create this account, ignore this email.

— The Dealzim Team
            """
            mail.send(msg)
            flash('Account created! Check your email to verify your account.', 'success')
        except Exception:
            flash(
                'Account created! We could not send your verification email. '
                'Use the Resend Verification option after logging in.',
                'info'
            )
        finally:
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/verify/<token>')
def verify_email(token):
    try:
        email = serializer.loads(token, salt='email-verify', max_age=21600)
    except SignatureExpired:
        flash('Your verification link has expired. Please request a new one.', 'danger')
        return redirect(url_for('resend_verification'))
    except BadSignature:
        flash('Invalid verification link.', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('register'))

    if user.is_verified:
        flash('Your email is already verified. Please login.', 'info')
        return redirect(url_for('login'))

    user.is_verified = True
    db.session.commit()
    flash('Email verified successfully! You can now post listings.', 'success')
    return redirect(url_for('login'))


@app.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('No account found with that email.', 'danger')
            return redirect(url_for('resend_verification'))

        if user.is_verified:
            flash('This account is already verified.', 'info')
            return redirect(url_for('login'))

        token = serializer.dumps(email, salt='email-verify')
        verify_url = url_for('verify_email', token=token, _external=True)

        try:
            msg = Message(
                subject='Verify your Dealzim account',
                recipients=[email]
            )
            msg.body = f"""
Hi {user.fullname},

Here is your new Dealzim verification link.
This link expires in 6 hours.

{verify_url}

— The Dealzim Team
            """
            mail.send(msg)
            flash('Verification email resent. Check your inbox.', 'success')
        except Exception:
            flash('Could not send email. Try again later.', 'danger')

        return redirect(url_for('login'))

    return render_template('resend_verification.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').lower().strip()
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User.query.filter_by(email=username).first()

        if not user or not check_password_hash(user.password, password):
            flash('Incorrect username or password.', 'danger')
            return redirect(url_for('login'))

        if user.is_banned:
            flash('Your account has been banned. Contact support.', 'danger')
            return redirect(url_for('login'))

        login_user(user)
        flash(f'Welcome back, @{user.username}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    listings = Listing.query.filter_by(user_id=current_user.id)\
               .order_by(Listing.date_posted.desc()).all()
    return render_template('dashboard.html', user=current_user, listings=listings)

@app.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    if not current_user.is_verified:
        flash('Please verify your email before posting listings.', 'danger')
        return redirect(url_for('resend_verification'))
    if request.method == 'POST':
        title = request.form.get('title')
        price = request.form.get('price')
        description = request.form.get('description')
        location = request.form.get('location')
        category = request.form.get('category', 'Other')

        image_filename = 'no-image.png'
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{current_user.username}_{int(datetime.now().timestamp())}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            image_filename = unique_filename

        new_listing = Listing(
            title=title,
            price=float(price),
            description=description,
            location=location,
            category=category,
            image=image_filename,
            user_id=current_user.id
        )
        db.session.add(new_listing)
        db.session.commit()
        flash('Your deal has been posted!', 'success')
        return redirect(url_for('listing', id=new_listing.id))

    return render_template('post.html', categories=CATEGORIES)

@app.route('/listing/<int:id>')
def listing(id):
    item = Listing.query.get_or_404(id)
    seller = db.session.get(User, item.user_id)

    whatsapp_share_url = (
        f"https://wa.me/?text="
        f"*{item.title}*%0A"
        f"Price: ₦{item.price:,.0f}%0A"
        f"Seller: @{seller.username}%0A"
        f"Location: {item.location}%0A"
        f"Category: {item.category}%0A"
        f"Posted via Dealzim%0A"
        f"👉 https://dealzim.com/listing/{item.id}"
    )

    whatsapp_contact_url = (
        f"https://wa.me/{seller.whatsapp.replace('+', '').replace(' ', '')}"
        f"?text=Hi%20@{seller.username},%20I%20saw%20your%20listing%20on%20Dealzim:%20"
        f"*{item.title}*%20(₦{item.price:,.0f}).%20Is%20it%20still%20available?"
    )

    return render_template('listing.html',
                           listing=item,
                           seller=seller,
                           whatsapp_share_url=whatsapp_share_url,
                           whatsapp_contact_url=whatsapp_contact_url)

@app.route('/delete/<int:id>')
@login_required
def delete_listing(id):
    item = Listing.query.get_or_404(id)
    if item.user_id != current_user.id:
        flash('You can only delete your own listings.', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(item)
    db.session.commit()
    flash('Listing deleted.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/category/<category_name>')
def category(category_name):
    listings = Listing.query.filter_by(
        category=category_name,
        is_approved=True
    ).order_by(Listing.date_posted.desc()).all()
    return render_template('category.html',
                           listings=listings,
                           category_name=category_name,
                           categories=CATEGORIES)

# ══════════════════════════════════════
# ADMIN ROUTES
# ══════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()

        if not admin or not check_password_hash(admin.password, password):
            flash('Incorrect admin credentials.', 'danger')
            return redirect(url_for('admin_login'))

        session['admin_logged_in'] = True
        session['admin_username'] = admin.username
        flash('Welcome, Admin.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Admin logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.joined.desc()).all()
    listings = Listing.query.order_by(Listing.date_posted.desc()).all()
    return render_template('admin/dashboard.html',
                           users=users,
                           listings=listings,
                           total_users=len(users),
                           total_listings=len(listings))

@app.route('/admin/delete-listing/<int:id>')
@admin_required
def admin_delete_listing(id):
    item = Listing.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash(f'Listing "{item.title}" deleted.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/ban-user/<int:id>')
@admin_required
def admin_ban_user(id):
    user = db.session.get(User, id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
    user.is_banned = True
    db.session.commit()
    flash(f'User @{user.username} has been banned.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unban-user/<int:id>')
@admin_required
def admin_unban_user(id):
    user = db.session.get(User, id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
    user.is_banned = False
    db.session.commit()
    flash(f'User @{user.username} has been unbanned.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-user/<int:id>')
@admin_required
def admin_delete_user(id):
    user = db.session.get(User, id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
    Listing.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f'User @{user.username} and all their listings deleted.', 'info')
    return redirect(url_for('admin_dashboard'))
# ══════════════════════════════════════
# WHATSAPP CONTACT KEY
# ══════════════════════════════════════

@app.route('/download-contacts')
@login_required
def download_contacts():
    from flask import Response
    from datetime import datetime

    # Time window: 6AM to 4PM
    now = datetime.now()
    window_start = now.replace(hour=6, minute=0, second=0)
    window_end = now.replace(hour=16, minute=0, second=0)

    if not (window_start <= now <= window_end):
        flash('Contact downloads are only available between 6:00 AM and 4:00 PM daily.', 'info')
        return redirect(url_for('dashboard'))

    # Get all users except the current user
    users = User.query.filter(
        User.id != current_user.id,
        User.is_banned == False
    ).all()

    if not users:
        flash('No contacts available to download yet.', 'info')
        return redirect(url_for('dashboard'))

    # Build the .vcf file
    vcf_lines = []
    for user in users:
        # Clean the WhatsApp number
        number = user.whatsapp.strip().replace(' ', '').replace('-', '')
        if not number.startswith('+'):
            number = '+' + number

        # Format contact name
        contact_name = f"{user.fullname} ({user.location}) - Dealzim"

        vcf_lines.append("BEGIN:VCARD")
        vcf_lines.append("VERSION:3.0")
        vcf_lines.append(f"FN:{contact_name}")
        vcf_lines.append(f"TEL;TYPE=CELL:{number}")
        vcf_lines.append("END:VCARD")
        vcf_lines.append("")

    vcf_content = "\n".join(vcf_lines)

    return Response(
        vcf_content,
        mimetype='text/vcard',
        headers={
            'Content-Disposition': 'attachment; filename=dealzim-contacts.vcf'
        }
    )

if __name__ == '__main__':
    app.run(debug=True)
