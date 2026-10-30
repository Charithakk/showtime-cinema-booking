
import smtplib
from email.message import EmailMessage


def send_booking_email(app, recipient, booking):

    cfg = app.config

    username = cfg.get("MAIL_USERNAME", "").strip()
    password = cfg.get("MAIL_PASSWORD", "").replace(" ", "").strip()
    sender = cfg.get("MAIL_FROM", "").strip()

    if not username or not password or not sender:
        app.logger.error(
            "EMAIL FAILED: SMTP credentials are missing."
        )
        return False

    message = EmailMessage()

    message["Subject"] = (
        f"SHOWTIME Ticket Confirmed - {booking.booking_code}"
    )

    message["From"] = sender
    message["To"] = recipient

    message.set_content(
        f"""
Hello!

Your SHOWTIME booking is confirmed.

Movie: {booking.movie.title}

Date: {booking.show_date}

Showtime: {booking.show_time}

Seats: {booking.seats}

Amount: Rs. {booking.amount}

Booking ID: {booking.booking_code}

Payment Status: {booking.payment_status}

Thank you for booking with SHOWTIME!

Enjoy your movie.
"""
    )

    try:

        app.logger.info(
            "Connecting to Gmail SMTP server..."
        )

        with smtplib.SMTP(
            cfg.get("MAIL_SERVER", "smtp.gmail.com"),
            int(cfg.get("MAIL_PORT", 587)),
            timeout=20
        ) as server:

            server.ehlo()
            server.starttls()
            server.ehlo()

            server.login(
                username,
                password
            )

            server.send_message(message)

        app.logger.info(
            "EMAIL SUCCESS: Confirmation sent to %s",
            recipient
        )

        return True

    except Exception:
        app.logger.exception(
            "EMAIL FAILED: Gmail SMTP error"
        )
        return False
