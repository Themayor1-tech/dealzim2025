from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

CATEGORIES = [
    'Electronics',
    'Fashion & Clothing',
    'Food & Drinks',
    'Books & Stationery',
    'Services',
    'Furniture & Home',
    'Health & Beauty',
    'Sports & Fitness',
    'Vehicles & Transport',
    'Other'
]

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='both')
    is_banned = db.Column(db.Boolean, default=False)
    joined = db.Column(db.DateTime, default=datetime.utcnow)
    listings = db.relationship('Listing', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='Other')
    image = db.Column(db.String(200), default='no-image.png')
    is_approved = db.Column(db.Boolean, default=True)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Listing {self.title}>'


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<Admin {self.username}>'
