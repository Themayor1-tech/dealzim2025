from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Listing, Admin
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'dealzim-secret-key-change-later'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dealzim.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    # Create default admin if none exists
    if not Admin.query.first():
        default_admin = Admin(
            username='admin',
            password=generate_password_hash('dealzim2025')
        )
        db.session.add(default_admin)
        db.session.commit()

# ── Admin login required decorator ──
from functools import wraps
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
    listings = Listing.query.filter_by(is_approved=True)\
               .order_by(Listing.date_posted.desc()).all()
    return render_template('home.html', listings=listings)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        username = request.form.get('username').lower().strip()
        whatsapp = request.form.get('whatsapp')
        location = request.form.get('location')
        password = request.form.get('password')
        role = request.form.get('role')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('That username is already taken. Choose another.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(
            fullname=fullname,
            username=username,
            whatsapp=whatsapp,
            location=location,
            password=hashed_password,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').lower().strip()
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

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
    if request.method == 'POST':
        title = request.form.get('title')
        price = request.form.get('price')
        description = request.form.get('description')
        location = request.form.get('location')

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
            image=image_filename,
            user_id=current_user.id
        )
        db.session.add(new_listing)
        db.session.commit()
        flash('Your deal has been posted!', 'success')
        return redirect(url_for('listing', id=new_listing.id))

    return render_template('post.html')

@app.route('/listing/<int:id>')
def listing(id):
    item = Listing.query.get_or_404(id)
    seller = db.session.get(User, item.user_id)
    whatsapp_url = (
        f"https://wa.me/?text="
        f"*{item.title}*%0A"
        f"Price: ₦{item.price:,.0f}%0A"
        f"Seller: @{seller.username}%0A"
        f"Location: {item.location}%0A"
        f"Posted via Dealzim%0A"
        f"👉 https://dealzim.com/listing/{item.id}"
    )
    return render_template('listing.html', listing=item,
                           seller=seller, whatsapp_url=whatsapp_url)

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
    total_users = len(users)
    total_listings = len(listings)
    return render_template('admin/dashboard.html',
                           users=users,
                           listings=listings,
                           total_users=total_users,
                           total_listings=total_listings)

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
    # Delete all their listings first
    Listing.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f'User @{user.username} and all their listings deleted.', 'info')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
