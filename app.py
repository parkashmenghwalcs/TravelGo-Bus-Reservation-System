
from flask import Flask, render_template, request, redirect, url_for, flash
from database import get_connection
from datetime import datetime, date
import webbrowser
from threading import Timer

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-before-deployment"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search")
def search_buses():
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    travel_date = request.args.get("date", "").strip()

    if not source or not destination or not travel_date:
        return "Please select source, destination and travel date.", 400

    try:
        selected_date = datetime.strptime(travel_date, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid travel date.", 400

    if selected_date < date.today():
        return "Travel date cannot be in the past.", 400

    if source == destination:
        return "Departure and destination cannot be the same.", 400

    connection = get_connection()

    buses = connection.execute("""
        SELECT
            buses.*,
            buses.total_seats - COALESCE(
                (SELECT SUM(bookings.seats)
                 FROM bookings
                 WHERE bookings.bus_id = buses.id
                 AND bookings.travel_date = ?), 0
            ) AS available_seats
        FROM buses
        WHERE buses.source = ? AND buses.destination = ?
        ORDER BY buses.departure_time
    """, (travel_date, source, destination)).fetchall()

    connection.close()

    return render_template(
        "buses.html",
        buses=buses,
        source=source,
        destination=destination,
        travel_date=travel_date
    )


@app.route("/book/<int:bus_id>", methods=["GET", "POST"])
def book_ticket(bus_id):
    travel_date = request.values.get("travel_date", "").strip()

    if not travel_date:
        return "Travel date is required. Please search again.", 400

    try:
        selected_date = datetime.strptime(travel_date, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid travel date.", 400

    if selected_date < date.today():
        return "Travel date cannot be in the past.", 400

    connection = get_connection()

    bus = connection.execute(
        "SELECT * FROM buses WHERE id = ?", (bus_id,)
    ).fetchone()

    if bus is None:
        connection.close()
        return "Bus not found.", 404

    if request.method == "POST":
        passenger_name = request.form.get("passenger_name", "").strip()
        passenger_email = request.form.get("passenger_email", "").strip()

        try:
            seats = int(request.form.get("seats", "0"))
        except ValueError:
            seats = 0

        if not passenger_name or not passenger_email or seats < 1:
            connection.close()
            return "Please enter valid passenger details and seat quantity.", 400

        if len(passenger_name) > 100 or len(passenger_email) > 150:
            connection.close()
            return "Passenger details are too long.", 400

        if "@" not in passenger_email or "." not in passenger_email:
            connection.close()
            return "Please enter a valid email address.", 400

        try:
            # Lock the database while checking and saving the booking.
            connection.execute("BEGIN IMMEDIATE")

            reserved = connection.execute("""
                SELECT COALESCE(SUM(seats), 0)
                FROM bookings
                WHERE bus_id = ? AND travel_date = ?
            """, (bus_id, travel_date)).fetchone()[0]

            available = bus["total_seats"] - reserved

            if seats > available:
                connection.rollback()
                connection.close()
                return (
                    f"Only {available} seat(s) are available. "
                    "Please search again and choose fewer seats."
                ), 400

            total_fare = seats * bus["fare"]

            cursor = connection.execute("""
                INSERT INTO bookings
                (bus_id, passenger_name, passenger_email,
                 seats, travel_date, total_fare)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                bus_id,
                passenger_name,
                passenger_email,
                seats,
                travel_date,
                total_fare
            ))

            booking_id = cursor.lastrowid
            connection.commit()
            connection.close()

            return redirect(
                url_for("booking_confirmation", booking_id=booking_id)
            )

        except Exception:
            connection.rollback()
            connection.close()
            app.logger.exception("Booking failed")
            return "Booking could not be completed. Please try again.", 500

    reserved = connection.execute("""
        SELECT COALESCE(SUM(seats), 0)
        FROM bookings
        WHERE bus_id = ? AND travel_date = ?
    """, (bus_id, travel_date)).fetchone()[0]

    available_seats = bus["total_seats"] - reserved
    connection.close()

    if available_seats < 1:
        return "Sorry, this bus is fully booked for that date.", 400

    return render_template(
        "booking.html",
        bus=bus,
        travel_date=travel_date,
        available_seats=available_seats
    )


@app.route("/confirmation/<int:booking_id>")
def booking_confirmation(booking_id):
    connection = get_connection()

    booking = connection.execute("""
        SELECT
            bookings.*,
            buses.bus_name,
            buses.source,
            buses.destination,
            buses.departure_time
        FROM bookings
        JOIN buses ON bookings.bus_id = buses.id
        WHERE bookings.id = ?
    """, (booking_id,)).fetchone()

    connection.close()

    if booking is None:
        return "Booking not found.", 404

    return render_template("confirmation.html", booking=booking)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
