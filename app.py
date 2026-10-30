
import os
import uuid
import hmac
import hashlib
from datetime import date

from flask import Flask, jsonify, request, render_template
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError

from config import Config
from models import db, User, Movie, Booking
from services.email_service import send_booking_email


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
JWTManager(app)


# ---------------- MOVIE COLLECTION ----------------

MOVIES = [
    ("They Call Him OG", 2025, "A feared gangster returns to Mumbai's underworld.", "Action / Crime", 0),
    ("Johnny", 2003, "A kickboxer fights to protect the woman he loves.", "Action / Drama", 1),
    ("Panjaa", 2011, "A loyal enforcer faces a dangerous conflict.", "Action / Thriller", 2),
    ("Balu", 2005, "A man with a mysterious past faces rivalry and romance.", "Action / Romance", 3),
    ("Thammudu", 1999, "A young man takes on a life-changing challenge.", "Sports / Drama", 4),
    ("Tholi Prema", 1998, "A young man's first experience of love.", "Romance / Drama", 99),
    ("Badri", 2000, "A young man gets caught between friendship and love.", "Romance / Action", 99),
    ("Kushi", 2001, "Friendship slowly turns into love.", "Romance / Comedy", 99),
    ("Gudumba Shankar", 2004, "A clever young man helps a woman.", "Action / Comedy", 99),
    ("Annavaram", 2006, "A protective brother fights to keep his sister safe.", "Action / Drama", 99),
    ("Bangaram", 2006, "A journalist becomes involved in an unexpected mission.", "Action / Drama", 99),
    ("Teen Maar", 2011, "A modern chef discovers a different view of love.", "Romance / Comedy", 99),
    ("Jalsa", 2008, "A man with a complicated past finds love and purpose.", "Action / Comedy", 99),
    ("Cameraman Gangatho Rambabu", 2012, "A cameraman fights corruption through media.", "Action / Political drama", 99),
    ("Gabbar Singh", 2012, "A fearless police officer takes on a local strongman.", "Action / Comedy", 99),
    ("Attarintiki Daredi", 2013, "A grandson tries to reunite a divided family.", "Family / Comedy", 99),
    ("Gopala Gopala", 2015, "A shopkeeper challenges blind faith.", "Comedy / Drama", 99),
    ("Sardaar Gabbar Singh", 2016, "A police officer protects people from a powerful villain.", "Action", 99),
    ("Katamarayudu", 2017, "A man confronts his beliefs to protect his family.", "Action / Family", 99),
    ("Agnyaathavaasi", 2018, "A mysterious man enters a powerful business family.", "Action / Drama", 99),
    ("Vakeel Saab", 2021, "A lawyer defends three young women.", "Legal / Drama", 99),
    ("Bheemla Nayak", 2022, "A police officer clashes with an ex-serviceman.", "Action / Drama", 99),
    ("Puli", 2010, "A young man fights for justice.", "Action / Fantasy", 99),
]


def seed_movies():
    if Movie.query.count() == 0:
        for title, year, description, genre, order in MOVIES:
            db.session.add(
                Movie(
                    title=title,
                    year=year,
                    description=description,
                    genre=genre,
                    poster_url="/static/images/og.jpg" if title == "They Call Him OG" else "",
                    featured_order=order
                )
            )
        db.session.commit()


# ---------------- HOME AND HEALTH ----------------

@app.get("/")
def home():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify(status="ok")


# ---------------- MOVIES ----------------

@app.get("/api/movies")
def get_movies():
    movies = Movie.query.order_by(
        Movie.featured_order,
        Movie.title
    ).all()

    return jsonify([
        {
            "id": movie.id,
            "title": movie.title,
            "year": movie.year,
            "description": movie.description,
            "genre": movie.genre,
            "poster_url": movie.poster_url,
            "featured": movie.featured_order < 5
        }
        for movie in movies
    ])


# ---------------- SIGNUP ----------------

@app.post("/api/signup")
def signup():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not name or not email or len(password) < 8:
        return jsonify(
            message="Enter your name, email and a password of at least 8 characters."
        ), 400

    if User.query.filter_by(email=email).first():
        return jsonify(
            message="An account with this email already exists."
        ), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password)
    )

    try:
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))

        return jsonify(
            message="Account created successfully.",
            token=token,
            user={
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        ), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify(
            message="An account with this email already exists."
        ), 409

    except Exception:
        db.session.rollback()
        app.logger.exception("Signup failed")
        return jsonify(
            message="Registration failed. Please try again."
        ), 500


# ---------------- LOGIN ----------------

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(message="Invalid email or password."), 401

    token = create_access_token(identity=str(user.id))

    return jsonify(
        message="Login successful.",
        token=token,
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    )


# ---------------- CURRENT USER ----------------

@app.get("/api/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))

    if not user:
        return jsonify(message="User not found."), 404

    return jsonify(
        id=user.id,
        name=user.name,
        email=user.email
    )


# ---------------- BOOKED SEATS ----------------

@app.get("/api/booked-seats")
def booked_seats():
    movie_id = request.args.get("movie_id", type=int)
    show_date = request.args.get("date", date.today().isoformat())
    show_time = request.args.get("time", "18:30")

    bookings = Booking.query.filter_by(
        movie_id=movie_id,
        show_date=show_date,
        show_time=show_time,
        payment_status="PAID"
    ).all()

    seats = [
        seat
        for booking in bookings
        for seat in booking.seats.split(",")
    ]

    return jsonify(seats=seats)


# ---------------- CREATE BOOKING / PAYMENT ORDER ----------------

@app.post("/api/create-order")
@jwt_required()
def create_order():
    data = request.get_json(silent=True) or {}

    movie = db.session.get(Movie, data.get("movie_id"))
    seats = sorted(set(data.get("seats", [])))

    if not movie or not seats or len(seats) > 8:
        return jsonify(
            message="Choose a movie and between 1 and 8 seats."
        ), 400

    show_date = data.get("date")
    show_time = data.get("time")

    if not show_date or not show_time:
        return jsonify(
            message="Choose a date and showtime."
        ), 400

    existing = Booking.query.filter_by(
        movie_id=movie.id,
        show_date=show_date,
        show_time=show_time,
        payment_status="PAID"
    ).all()

    occupied = {
        seat
        for booking in existing
        for seat in booking.seats.split(",")
    }

    if occupied.intersection(seats):
        return jsonify(
            message="One or more selected seats have just been booked. Refresh seats."
        ), 409

    amount = len(seats) * 150
    order_id = None

    key_id = app.config.get("RAZORPAY_KEY_ID", "")
    key_secret = app.config.get("RAZORPAY_KEY_SECRET", "")

    if key_id and key_secret:
        import razorpay

        client = razorpay.Client(auth=(key_id, key_secret))

        order = client.order.create({
            "amount": amount * 100,
            "currency": "INR",
            "receipt": str(uuid.uuid4())
        })

        order_id = order["id"]

    booking = Booking(
        booking_code="CB" + uuid.uuid4().hex[:8].upper(),
        user_id=int(get_jwt_identity()),
        movie_id=movie.id,
        show_date=show_date,
        show_time=show_time,
        seats=",".join(seats),
        amount=amount,
        payment_status="PENDING",
        razorpay_order_id=order_id
    )

    db.session.add(booking)
    db.session.commit()

    return jsonify(
        booking_id=booking.id,
        booking_code=booking.booking_code,
        amount=amount,
        razorpay_order_id=order_id,
        key_id=key_id or None,
        demo_mode=not bool(order_id)
    )


# ---------------- EMAIL HELPER ----------------

def notify_booking_customer(booking):
    try:
        recipient = booking.user.email

        sent = send_booking_email(
            app,
            recipient,
            booking
        )

        if sent:
            app.logger.info(
                "Booking confirmation email sent to %s",
                recipient
            )
        else:
            app.logger.error(
                "Booking is PAID, but email was not sent to %s",
                recipient
            )

        return sent

    except Exception:
        app.logger.exception(
            "Could not process booking confirmation email"
        )
        return False


# ---------------- DEMO PAYMENT CONFIRMATION ----------------

@app.post("/api/confirm-demo-payment")
@jwt_required()
def confirm_demo_payment():
    data = request.get_json(silent=True) or {}

    booking = db.session.get(
        Booking,
        data.get("booking_id")
    )

    if not booking or booking.user_id != int(get_jwt_identity()):
        return jsonify(message="Booking not found."), 404

    booking.payment_status = "PAID"
    db.session.commit()

    email_sent = notify_booking_customer(booking)

    return jsonify(
        message="Demo payment successful.",
        booking_code=booking.booking_code,
        email_sent=email_sent
    )


# ---------------- RAZORPAY PAYMENT VERIFICATION ----------------

@app.post("/api/verify-payment")
@jwt_required()
def verify_payment():
    data = request.get_json(silent=True) or {}

    booking = db.session.get(
        Booking,
        data.get("booking_id")
    )

    if not booking or booking.user_id != int(get_jwt_identity()):
        return jsonify(message="Booking not found."), 404

    secret = app.config.get("RAZORPAY_KEY_SECRET", "")

    if not secret:
        return jsonify(
            message="Razorpay is not configured."
        ), 400

    body = (
        f'{data.get("razorpay_order_id")}|'
        f'{data.get("razorpay_payment_id")}'
    ).encode()

    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        expected,
        data.get("razorpay_signature", "")
    ):
        return jsonify(
            message="Payment signature verification failed."
        ), 400

    if booking.razorpay_order_id != data.get("razorpay_order_id"):
        return jsonify(message="Order mismatch."), 400

    booking.payment_status = "PAID"
    db.session.commit()

    email_sent = notify_booking_customer(booking)

    return jsonify(
        message="Payment verified.",
        booking_code=booking.booking_code,
        email_sent=email_sent
    )


# ---------------- MY BOOKINGS ----------------

@app.get("/api/my-bookings")
@jwt_required()
def my_bookings():
    try:
        user_id = int(get_jwt_identity())

        bookings = Booking.query.filter_by(
            user_id=user_id
        ).order_by(
            Booking.created_at.desc()
        ).all()

        result = []

        for booking in bookings:
            movie_title = (
                booking.movie.title
                if booking.movie
                else "Unknown Movie"
            )

            show_date = (
                booking.show_date.isoformat()
                if hasattr(booking.show_date, "isoformat")
                else str(booking.show_date or "N/A")
            )

            show_time = str(booking.show_time or "N/A")

            result.append({
                "id": booking.id,
                "code": booking.booking_code,
                "booking_code": booking.booking_code,
                "movie": movie_title,
                "movie_title": movie_title,
                "date": show_date,
                "show_date": show_date,
                "time": show_time,
                "show_time": show_time,
                "seats": booking.seats,
                "amount": booking.amount,
                "status": booking.payment_status,
                "payment_status": booking.payment_status
            })

        return jsonify(result), 200

    except Exception:
        db.session.rollback()
        app.logger.exception("Could not retrieve user bookings")
        return jsonify(message="Unable to load bookings."), 500


# ---------------- DATABASE INITIALIZATION ----------------

with app.app_context():
    print(
        "DATABASE IN USE:",
        db.engine.url.render_as_string(hide_password=True)
    )

    db.create_all()
    seed_movies()


# ---------------- START APPLICATION ----------------

if __name__ == "__main__":
    app.run(
        debug=True,
        port=int(os.getenv("PORT", 5000))
    )
