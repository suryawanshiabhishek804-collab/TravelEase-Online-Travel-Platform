import os
import re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy import inspect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-development-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///travelease.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    bookings = db.relationship("Booking", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Destination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(80), default="Popular")


class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_per_night = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    rating = db.Column(db.Float, default=4.5)
    amenities = db.Column(db.Text, nullable=False, default="")


class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    destination = db.Column(db.String(120), nullable=False)
    duration = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    item_type = db.Column(db.String(30), nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    travel_date = db.Column(db.String(30), nullable=False)
    travellers = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default="Confirmed")
    payment_status = db.Column(db.String(30), default="Demo paid")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(180), nullable=False, default="")
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


HOTEL_AMENITY_OPTIONS = [
    ("wifi", "Free Wi-Fi"),
    ("pool", "Swimming pool"),
    ("parking", "Free parking"),
    ("breakfast", "Breakfast"),
    ("restaurant", "Restaurant"),
    ("mountain_views", "Mountain views"),
]

SEEDED_HOTEL_AMENITIES = {
    "Seabreeze Retreat": "wifi,pool,parking,breakfast,restaurant",
    "Himalayan View Lodge": "wifi,parking,restaurant,mountain_views",
    "Royal Heritage Stay": "wifi,pool,parking,breakfast,restaurant",
}


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year, "today": datetime.now().strftime("%Y-%m-%d")}


@app.route("/")
def home():
    destinations = Destination.query.limit(6).all()
    packages = Package.query.limit(3).all()
    hotels = Hotel.query.limit(3).all()
    return render_template("home.html", destinations=destinations, packages=packages, hotels=hotels)


@app.route("/destinations")
def destinations():
    q = request.args.get("q", "").strip()
    requested_category = request.args.get("category", "").strip()
    categories = [
        row[0] for row in
        db.session.query(Destination.category)
        .filter(Destination.category.isnot(None), Destination.category != "")
        .distinct()
        .order_by(Destination.category)
        .all()
    ]
    category = next(
        (name for name in categories if name.casefold() == requested_category.casefold()),
        "",
    )
    query = Destination.query
    if q:
        query = query.filter(db.or_(Destination.name.ilike(f"%{q}%"),
                                    Destination.state.ilike(f"%{q}%"),
                                    Destination.description.ilike(f"%{q}%"),
                                    Destination.category.ilike(f"%{q}%")))
    if category:
        query = query.filter(Destination.category == category)
    return render_template(
        "destinations.html",
        destinations=query.order_by(Destination.name).all(),
        categories=categories,
        category=category,
        q=q,
    )


@app.route("/hotels")
def hotels():
    q = request.args.get("q", "").strip()
    price_range = request.args.get("price", "").strip()
    min_rating = request.args.get("rating", "").strip()
    selected_amenities = [
        amenity for amenity in request.args.getlist("amenity")
        if amenity in dict(HOTEL_AMENITY_OPTIONS)
    ]
    query = Hotel.query
    if q:
        query = query.filter(db.or_(Hotel.name.ilike(f"%{q}%"), Hotel.city.ilike(f"%{q}%")))
    price_ranges = {
        "under-4000": (None, 3999),
        "4000-6000": (4000, 6000),
        "over-6000": (6001, None),
    }
    if price_range in price_ranges:
        minimum_price, maximum_price = price_ranges[price_range]
        if minimum_price is not None:
            query = query.filter(Hotel.price_per_night >= minimum_price)
        if maximum_price is not None:
            query = query.filter(Hotel.price_per_night <= maximum_price)
    if min_rating in {"4", "4.5"}:
        query = query.filter(Hotel.rating >= float(min_rating))
    for amenity in selected_amenities:
        query = query.filter(db.or_(
            Hotel.amenities.ilike(f"{amenity},%"),
            Hotel.amenities.ilike(f"%,{amenity},%"),
            Hotel.amenities.ilike(f"%,{amenity}"),
            Hotel.amenities == amenity,
        ))
    return render_template(
        "hotels.html",
        hotels=query.order_by(Hotel.price_per_night).all(),
        q=q,
        price_range=price_range if price_range in price_ranges else "",
        min_rating=min_rating if min_rating in {"4", "4.5"} else "",
        selected_amenities=selected_amenities,
        amenity_options=HOTEL_AMENITY_OPTIONS,
        amenity_labels=dict(HOTEL_AMENITY_OPTIONS),
    )


@app.route("/packages")
def packages():
    q = request.args.get("q", "").strip()
    budget = request.args.get("budget", "").strip()
    duration = request.args.get("duration", "").strip()
    requested_category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "").strip()

    category_rows = (
        db.session.query(Destination.name, Destination.category)
        .join(Package, Package.destination == Destination.name)
        .filter(Destination.category.isnot(None), Destination.category != "")
        .distinct()
        .all()
    )
    categories = sorted({category for _, category in category_rows})
    category_by_destination = {
        destination: category for destination, category in category_rows
    }
    category = next(
        (name for name in categories if name.casefold() == requested_category.casefold()),
        "",
    )

    query = Package.query
    if q:
        query = query.filter(db.or_(
            Package.title.ilike(f"%{q}%"),
            Package.destination.ilike(f"%{q}%"),
        ))

    budget_ranges = {
        "under-10000": (None, 9999),
        "10000-15000": (10000, 15000),
        "over-15000": (15001, None),
    }
    if budget in budget_ranges:
        minimum_price, maximum_price = budget_ranges[budget]
        if minimum_price is not None:
            query = query.filter(Package.price >= minimum_price)
        if maximum_price is not None:
            query = query.filter(Package.price <= maximum_price)
    if category:
        query = query.join(
            Destination, Package.destination == Destination.name
        ).filter(Destination.category == category)

    if sort == "price_desc":
        query = query.order_by(Package.price.desc(), Package.title)
    else:
        query = query.order_by(Package.price, Package.title)
        if sort not in {"", "price_asc"}:
            sort = ""

    packages_list = query.all()
    duration_days = {"weekend": (None, 3), "short": (4, 5), "week-plus": (6, None)}
    if duration in duration_days:
        minimum_days, maximum_days = duration_days[duration]

        def matches_duration(package):
            match = re.search(r"\d+", package.duration or "")
            days = int(match.group()) if match else None
            return days is not None and (
                (minimum_days is None or days >= minimum_days)
                and (maximum_days is None or days <= maximum_days)
            )

        packages_list = [package for package in packages_list if matches_duration(package)]
    else:
        duration = ""

    return render_template(
        "packages.html",
        packages=packages_list,
        q=q,
        budget=budget if budget in budget_ranges else "",
        duration=duration,
        category=category,
        categories=categories,
        sort=sort,
        category_by_destination=category_by_destination,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email and a password of at least 8 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "warning")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome to TravelEase! Your account is ready.", "success")
            return redirect(url_for("home"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("You are now logged in.", "success")
            return redirect(url_for("admin" if user.is_admin else "dashboard"))
        flash("Incorrect email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route("/book/<kind>/<int:item_id>", methods=["GET", "POST"])
@login_required
def book(kind, item_id):
    model = {"hotel": Hotel, "package": Package}.get(kind)
    if not model:
        abort(404)
    item = db.session.get(model, item_id)
    if not item:
        abort(404)
    if request.method == "POST":
        try:
            travellers = int(request.form.get("travellers", "1"))
            if not 1 <= travellers <= 20:
                raise ValueError()
        except ValueError:
            flash("Travellers must be between 1 and 20.", "danger")
            return render_template("booking.html", item=item, kind=kind)
        travel_date = request.form.get("travel_date", "")
        if not travel_date:
            flash("Please select a travel date.", "danger")
            return render_template("booking.html", item=item, kind=kind)
        unit_price = item.price_per_night if kind == "hotel" else item.price
        reference = f"TE{datetime.utcnow().strftime('%y%m%d')}{os.urandom(3).hex().upper()}"
        booking = Booking(reference=reference, user_id=current_user.id,
                          item_type=kind.title(), item_name=item.name if kind == "hotel" else item.title,
                          travel_date=travel_date, travellers=travellers,
                          total_price=unit_price * travellers)
        db.session.add(booking)
        db.session.commit()
        return redirect(url_for("payment", booking_id=booking.id))
    return render_template("booking.html", item=item, kind=kind)


@app.route("/payment/<int:booking_id>", methods=["GET", "POST"])
@login_required
def payment(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking or (booking.user_id != current_user.id and not current_user.is_admin):
        abort(404)
    if request.method == "POST":
        booking.payment_status = "Demo paid"
        booking.status = "Confirmed"
        db.session.commit()
        flash("Demo payment successful. Your booking is confirmed.", "success")
        return redirect(url_for("dashboard"))
    return render_template("payment.html", booking=booking)


@app.route("/dashboard")
@login_required
def dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template("dashboard.html", bookings=bookings)


@app.route("/cancel/<int:booking_id>", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.user_id != current_user.id:
        abort(404)
    if booking.status == "Confirmed":
        booking.status = "Cancellation requested"
        db.session.commit()
        flash("Cancellation request submitted.", "info")
    return redirect(url_for("dashboard"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    form_values = {"name": "", "email": "", "subject": "", "message": ""}
    if request.method == "POST":
        form_values = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "subject": request.form.get("subject", "").strip(),
            "message": request.form.get("message", "").strip(),
        }
        name = form_values["name"]
        email = form_values["email"]
        subject = form_values["subject"]
        message = form_values["message"]
        if not all(form_values.values()):
            flash("Please complete all fields before sending your message.", "danger")
        elif len(name) > 100 or len(email) > 150 or len(subject) > 180:
            flash("Please keep your name, email, and subject within the allowed length.", "danger")
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Please enter a valid email address.", "danger")
        elif len(message) > 10000:
            flash("Your message is too long. Please keep it under 10,000 characters.", "danger")
        else:
            db.session.add(ContactMessage(
                name=name,
                email=email,
                subject=subject,
                message=message,
            ))
            db.session.commit()
            flash("Thanks! Your message has been submitted.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html", form_values=form_values)


@app.route("/admin")
@admin_required
def admin():
    q = request.args.get("q", "").strip()
    user_query = db.session.query(
        User,
        db.func.count(Booking.id).label("booking_count"),
    ).outerjoin(Booking).group_by(User.id)
    if q:
        user_query = user_query.filter(db.or_(
            User.name.ilike(f"%{q}%"),
            User.email.ilike(f"%{q}%"),
        ))
    return render_template("admin.html",
        users=User.query.count(), bookings=Booking.query.count(),
        destinations=Destination.query.count(), packages=Package.query.count(),
        recent=Booking.query.order_by(Booking.created_at.desc()).limit(8).all(),
        users_with_bookings=user_query.order_by(User.name).all(),
        user_search=q,
        contact_messages=ContactMessage.query.order_by(
            ContactMessage.created_at.desc(), ContactMessage.id.desc()
        ).all())


@app.route("/admin/user/<int:user_id>")
@admin_required
def admin_user_details(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    bookings = Booking.query.filter_by(user_id=user.id).order_by(
        Booking.created_at.desc(), Booking.id.desc()
    ).all()
    return render_template(
        "admin_user.html",
        user=user,
        bookings=bookings,
        total_bookings=len(bookings),
    )


@app.route("/admin/booking/<int:booking_id>", methods=["POST"])
@admin_required
def admin_booking_status(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        abort(404)
    status = request.form.get("status")
    if status in ["Confirmed", "Cancellation requested", "Cancelled"]:
        booking.status = status
        db.session.commit()
        flash("Booking status updated.", "success")
    return redirect(url_for("admin"))


@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The page you requested could not be found."), 404


def seed_data():
    if Destination.query.first():
        for hotel in Hotel.query.filter(
            Hotel.name.in_(SEEDED_HOTEL_AMENITIES)
        ).all():
            if not hotel.amenities:
                hotel.amenities = SEEDED_HOTEL_AMENITIES[hotel.name]
        ladakh = Destination.query.filter_by(name="Ladakh", state="Ladakh").first()
        if ladakh and ladakh.image_url == "https://images.unsplash.com/photo-1581793745862-99a5564e8e97?w=1000":
            ladakh.image_url = "https://images.unsplash.com/photo-1598091383021-15ddea10925d?w=1000"
        admin_user = User.query.filter_by(email="traveladmin@travelease.local").first()
        if not admin_user:
            admin_user = User(name="TravelEase Admin", email="traveladmin@travelease.local", is_admin=True)
            db.session.add(admin_user)
        admin_user.is_admin = True
        admin_user.set_password("Admin@12345")
        db.session.commit()
        return
    destinations = [
        ("Goa", "Goa", "Sunny beaches, Portuguese heritage and lively coastal experiences.", "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=1000", "Beach"),
        ("Manali", "Himachal Pradesh", "Mountain views, pine forests and adventure in the Himalayas.", "https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?w=1000", "Mountain"),
        ("Jaipur", "Rajasthan", "Discover royal palaces, colourful markets and rich Rajasthani culture.", "https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?w=1000", "Heritage"),
        ("Kerala", "Kerala", "Relax among serene backwaters, tea gardens and tropical greenery.", "https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?w=1000", "Nature"),
        ("Mumbai", "Maharashtra", "Explore India's energetic city, iconic waterfront and food culture.", "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=1000", "City"),
        ("Ladakh", "Ladakh", "Experience dramatic high-altitude landscapes and mountain roads.", "https://images.unsplash.com/photo-1598091383021-15ddea10925d?w=1000", "Adventure"),
    ]
    for d in destinations:
        db.session.add(Destination(name=d[0], state=d[1], description=d[2], image_url=d[3], category=d[4]))
    hotels = [
        ("Seabreeze Retreat", "Goa", "A relaxed coastal stay close to the beach.", 4200, "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=1000", 4.7),
        ("Himalayan View Lodge", "Manali", "Cosy rooms with beautiful mountain views.", 3500, "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=1000", 4.6),
        ("Royal Heritage Stay", "Jaipur", "Traditional hospitality in a heritage-inspired setting.", 5100, "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=1000", 4.8),
    ]
    for h in hotels:
        db.session.add(Hotel(name=h[0], city=h[1], description=h[2], price_per_night=h[3], image_url=h[4], rating=h[5], amenities=SEEDED_HOTEL_AMENITIES.get(h[0], "")))
    packages = [
        ("Goa Beach Escape", "Goa", "3 Days / 2 Nights", 8999, "Beach time, local sightseeing and a relaxed coastal break.", "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=1000"),
        ("Manali Mountain Explorer", "Manali", "5 Days / 4 Nights", 14999, "Mountain sightseeing, local experiences and scenic drives.", "https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?w=1000"),
        ("Royal Jaipur Weekend", "Jaipur", "3 Days / 2 Nights", 10999, "Explore forts, palaces, markets and Rajasthani cuisine.", "https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?w=1000"),
    ]
    for p in packages:
        db.session.add(Package(title=p[0], destination=p[1], duration=p[2], price=p[3], description=p[4], image_url=p[5]))
    admin_user = User.query.filter_by(email="admin@travelease.local").first()
    if not admin_user:
        admin_user = User(name="TravelEase Admin", email="admin@travelease.local", is_admin=True)
        admin_user.set_password("Admin@12345")
        db.session.add(admin_user)
    db.session.commit()


with app.app_context():
    db.create_all()
    user_columns = {column["name"] for column in inspect(db.engine).get_columns("user")}
    if "created_at" not in user_columns:
        with db.engine.begin() as connection:
            connection.execute(
                db.text("ALTER TABLE user ADD COLUMN created_at DATETIME")
            )
    contact_message_columns = {
        column["name"] for column in inspect(db.engine).get_columns("contact_message")
    }
    if "subject" not in contact_message_columns:
        with db.engine.begin() as connection:
            connection.execute(
                db.text("ALTER TABLE contact_message ADD COLUMN subject VARCHAR(180) NOT NULL DEFAULT ''")
            )
    hotel_columns = {column["name"] for column in inspect(db.engine).get_columns("hotel")}
    if "amenities" not in hotel_columns:
        with db.engine.begin() as connection:
            connection.execute(
                db.text("ALTER TABLE hotel ADD COLUMN amenities TEXT NOT NULL DEFAULT ''")
            )
    seed_data()


if __name__ == "__main__":
    app.run(debug=True)
