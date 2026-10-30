from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), unique=True, nullable=False)
    year = db.Column(db.Integer)
    description = db.Column(db.Text)
    genre = db.Column(db.String(100), default="Drama")
    poster_url = db.Column(db.String(500), default="")
    featured_order = db.Column(db.Integer, default=99)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_code = db.Column(db.String(30), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey("movie.id"), nullable=False)
    show_date = db.Column(db.String(20), nullable=False)
    show_time = db.Column(db.String(20), nullable=False)
    seats = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    payment_status = db.Column(db.String(30), default="PENDING")
    razorpay_order_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")
    movie = db.relationship("Movie")
