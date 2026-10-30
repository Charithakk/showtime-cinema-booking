
import os
import resend


def send_booking_email(app, recipient, booking):

    api_key = (
        app.config.get("RESEND_API_KEY")
        or os.getenv("RESEND_API_KEY", "")
    ).strip()

    if not api_key:
        app.logger.error("EMAIL FAILED: RESEND_API_KEY is missing.")
        return False

    resend.api_key = api_key

    message = {
        "from": "SHOWTIME <onboarding@resend.dev>",
        "to": [recipient],
        "subject": f"SHOWTIME Ticket Confirmed - {booking.booking_code}",
        "text": f"""
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
    }

    try:
        app.logger.info("Sending booking confirmation through Resend...")

        resend.Emails.send(message)

        app.logger.info(
            "EMAIL SUCCESS: Confirmation sent to %s",
            recipient
        )

        return True

    except Exception:
        app.logger.exception("EMAIL FAILED: Resend API error")
        return False
