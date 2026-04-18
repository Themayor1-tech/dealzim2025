from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import os

app = Flask(__name__)
app.secret_key = 'dealzim-secret-key-change-later'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dealzim.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access that page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── Create tables on first run ──
with app.app_context():
    db.create_all()

# ── Routes ──

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        username = request.form.get('username').lower().strip()
        whatsapp = request.form.get('whatsapp')
        location = request.form.get('location')
        password = request.form.get('password')
        role = request.form.get('role')

        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('That username is already taken. Choose another.', 'danger')
            return redirect(url_for('register'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Create new user
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
    return render_template('dashboard.html', user=current_user)

@app.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    return render_template('post.html')

@app.route('/listing/<int:id>')
def listing(id):
    listing = {
        'id': id,
        'title': 'Sample Product',
        'price': '5,000',
        'description': 'This is a sample product description.',
        'seller': 'testuser',
        'location': 'University of Lagos',
        'date': 'April 2026'
    }
    whatsapp_url = (
        f"https://wa.me/?text="
        f"*{listing['title']}*%0A"
        f"Price: ₦{listing['price']}%0A"
        f"Seller: @{listing['seller']}%0A"
        f"Location: {listing['location']}%0A"
        f"Posted via Dealzim%0A"
        f"👉 http://127.0.0.1:5000/listing/{listing['id']}"
    )
    return render_template('listing.html', listing=listing, whatsapp_url=whatsapp_url)

if __name__ == '__main__':
    app.run(debug=True)
