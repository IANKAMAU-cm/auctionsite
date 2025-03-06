from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, UTC, timezone
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
import os
from werkzeug.utils import secure_filename
import uuid
from flask_migrate import Migrate
import pytz
import requests
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()  # Load environment variables from .env
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
app.config['SECRET_KEY'] = 'your_secret_key'
migrate = Migrate(app, db) 

# Initialize database with app
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Import models and forms
from models import User, AuctionItem, Bid, AdditionalImage, Notification, AlertSubscription
from forms import LoginForm, RegisterForm 

# Define Nairobi timezone
nairobi_tz = pytz.timezone("Africa/Nairobi")

UPLOAD_FOLDER = 'static/uploads'  # Folder to store uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.errorhandler(413)
def request_entity_too_large(error):
    return "File is too large! Please upload a file smaller than 5 MB.", 413


@app.context_processor
def inject_user_model():
    from models import User  # Import your User model here
    return dict(User=User)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    # Check if any admin exists
    existing_admin = User.query.filter_by(is_admin=True).first()
    if existing_admin:
        flash('Admin account already exists. Please contact an admin to create additional admin accounts.', 'danger')
        return redirect(url_for('admin_login'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # Check if username already exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('admin_register'))

        # Create new admin user
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_admin = User(username=form.username.data, password=hashed_password, is_admin=True)
        db.session.add(new_admin)
        db.session.commit()

        flash('Admin registration successful!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('register.html', form=form, is_admin=True)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.is_admin and check_password_hash(user.password, password):
            login_user(user)
            flash('Admin logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Unauthorized access!')
        return redirect(url_for('home'))
    auctions = AuctionItem.query.all()
    return render_template('admin_dashboard.html', auctions=auctions)

@app.route('/admin/add-auction', methods=['GET', 'POST'])
@login_required
def add_auction():
    if not current_user.is_admin:
        flash('Unauthorized access!')
        return redirect(url_for('home'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        starting_price = float(request.form['starting_price'])
        end_time_naive = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')  # Parse from form
        end_time_nairobi = nairobi_tz.localize(end_time_naive)  # Attach Nairobi timezone
        end_time_utc = end_time_nairobi.astimezone(pytz.utc)  # Convert to UTC
    
        category = request.form['category']  # Get selected category
        
        serial_number = request.form['serial_number'] or None
        model = request.form['model'] or None
        year_of_manufacture = request.form['year_of_manufacture'] or None
        color = request.form['color'] or None
        primary_damage = request.form['primary_damage'] or None
        secondary_damage = request.form['secondary_damage'] or None
        VIN = request.form['VIN'] or None
        odometer = request.form['odometer'] or None
        working = request.form['working'] or None
        sale_status='Open'  # Ensure this is set to 'Open'
        
        # Handle image upload
        if 'image' not in request.files:
            flash('No image file provided!')
            return redirect(request.url)
        file = request.files['image']
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            image_path = os.path.join('uploads', unique_filename)  # Only store the path relative to the 'static' folder
        else:
            flash('Invalid file type! Only images are allowed.')
            return redirect(request.url)
        
        auction_item = AuctionItem(title=title, description=description,
                                   starting_price=starting_price, image=image_path, end_time=end_time_utc, category=category, serial_number=serial_number, model=model, year_of_manufacture=year_of_manufacture, color=color, primary_damage=primary_damage, secondary_damage=secondary_damage, VIN=VIN, odometer=odometer, working=working, sale_status=sale_status)
        db.session.add(auction_item)
        db.session.commit()
        flash('Auction added successfully!')
        return redirect(url_for('admin_dashboard'))
    categories = ['Electronics', 'Furniture', 'Vehicles', 'Real Estate', 'Machinery', 'Featured']
    return render_template('add_auction.html', categories=categories)

@app.route('/admin/edit-auction/<int:auction_id>', methods=['GET', 'POST'])
@login_required
def edit_auction(auction_id):
    if not current_user.is_admin:
        flash('Unauthorized access!')
        return redirect(url_for('home'))
    auction_item = AuctionItem.query.get_or_404(auction_id)
    end_time_naive = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
    end_time_nairobi = nairobi_tz.localize(end_time_naive)
    end_time_utc = end_time_nairobi.astimezone(pytz.utc)
    categories = ['Electronics', 'Furniture', 'Vehicles', 'Real Estate', 'Machinery', 'Featured']  # Predefined categories

    if request.method == 'POST':
        auction_item.title = request.form['title']
        auction_item.description = request.form['description']
        auction_item.starting_price = float(request.form['starting_price'])
        auction_item.end_time = end_time_utc  # Save in UTC
        auction_item.category = request.form['category']  # Update category
        
        auction_item.serial_number = request.form['serial_number'] or None
        auction_item.model = request.form['model'] or None
        auction_item.year_of_manufacture = request.form['year_of_manufacture'] or None
        auction_item.color = request.form['color'] or None
        auction_item.primary_damage = request.form['primary_damage'] or None
        auction_item.secondary_damage = request.form['secondary_damage'] or None
        auction_item.VIN = request.form['VIN'] or None
        auction_item.odometer = request.form['odometer'] or None
        auction_item.working = request.form['working'] or None
        
        if auction_item.sale_status not in ['Sold', 'Closed']:
            auction_item.sale_status = 'Open'  # Keep it 'Open' unless it's Sold or Closed
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                auction_item.image = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        db.session.commit()
        flash('Auction updated successfully!')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_auction.html', auction_item=auction_item, categories=categories)

@app.route('/admin/delete-auction/<int:auction_id>')
@login_required
def delete_auction(auction_id):
    if not current_user.is_admin:
        flash('Unauthorized access!')
        return redirect(url_for('home'))
    auction_item = AuctionItem.query.get_or_404(auction_id)
    db.session.delete(auction_item)
    db.session.commit()
    flash('Auction deleted successfully!')
    return redirect(url_for('view_auctions'))

@app.route('/admin/view-auctions', methods=['GET'])
@login_required
def view_auctions():
    if not current_user.is_admin:
        flash('Unauthorized access!')
        return redirect(url_for('home'))
    auctions = AuctionItem.query.all()
    return render_template('view_auctions.html', auctions=auctions)

#Admin bid management logic
@app.route('/admin/bids')
def admin_bid_management():
    auction_items = db.session.query(AuctionItem).join(Bid).distinct().all()
    users = db.session.query(User).join(Bid).distinct().all()
    """Admin dashboard for managing bids."""
    return render_template('admin_bid_management.html', auction_items=auction_items, users=users)

@app.route('/admin/bids/all')
def view_all_bids():
    """View all bids placed by users."""
    bids = db.session.query(Bid, AuctionItem.title).join(User).join(AuctionItem).all()
    return render_template('view_all_bids.html', bids=bids)

@app.route('/admin/bids/history/<int:item_id>')
def view_bid_history(item_id):
    """View bidding history for a specific auction item."""
    auction = AuctionItem.query.get(item_id)  # Fetch auction item
    if not auction:
        abort(404)  # Handle the case where the auction item does not exist
    
    bids = Bid.query.filter_by(auction_id=item_id).order_by(Bid.timestamp.desc()).all()
    return render_template('view_bid_history.html', bids=bids, item_id=item_id, auction=auction)

@app.route('/admin/bids/user/<int:user_id>')
def view_user_bidding_history(user_id):
    #user_id = request.args.get('user_id')  # Get the selected user_id from the form
    if not user_id:
        return "User ID is required", 400  # Handle cases where no user is selected
    
    """View a specific user's bidding history."""
    user = User.query.get(user_id)  # Fetch user details
    if not user:
        flash("User not found", "danger")
        return redirect(url_for('admin_dashboard'))
    
    user_bids = Bid.query.filter_by(user_id=user_id).order_by(Bid.timestamp.desc()).all()
    return render_template('view_user_bidding_history.html', bids=user_bids, user=user, user_id=user_id)


@app.route('/admin/bids/delete/<int:bid_id>', methods=['POST'])
def delete_bid(bid_id):
    """Delete or cancel a bid."""
    bid = Bid.query.get_or_404(bid_id)
    db.session.delete(bid)
    db.session.commit()
    flash('Bid deleted successfully.', 'success')
    return redirect(url_for('view_all_bids'))

@app.route('/admin/bids/reports')
def auction_reports():
    """Generate auction summary reports."""
    ongoing_auctions = AuctionItem.query.filter_by(sale_status='Open').all()
    completed_auctions = AuctionItem.query.filter_by(sale_status='Closed').all()
    sold_auctions = AuctionItem.query.filter_by(sale_status='sold').all()  # Ensure you have this value in your DB

    return render_template(
        'auction_reports.html', 
        ongoing=ongoing_auctions, 
        completed=completed_auctions, 
        sold=sold_auctions
    )
    
@app.route('/admin/bids/reports/<report_type>')
def generate_report(report_type):
    """Generate specific auction reports based on type."""
    if report_type == 'ongoing':
        auctions = AuctionItem.query.filter_by(sale_status='Open').all()
    elif report_type == 'completed':
        auctions = AuctionItem.query.filter_by(sale_status='Closed').all()
    elif report_type == 'sold':
        auctions = AuctionItem.query.filter_by(sale_status='sold').all()
    else:
        flash("Invalid report type", "danger")
        return redirect(url_for('auction_reports'))

    return render_template('generated_report.html', auctions=auctions, report_type=report_type)




@app.route('/category/<string:category>')
@login_required
def view_category(category):
    page = request.args.get('page', 1, type=int)  # Get the page number from query parameters
    per_page = 10  # Number of items per page
    
    auctions = AuctionItem.query.filter_by(category=category).filter(AuctionItem.end_time > datetime.now(UTC)).paginate(page=page, per_page=per_page)
    print(AuctionItem.query.all())
    return render_template('category.html', auctions=auctions, category=category)



@app.route('/auction/<int:auction_id>', methods=['GET', 'POST'])
@login_required
def auction_details(auction_id):
    # Query the auction item from the database
    auction = AuctionItem.query.get_or_404(auction_id)
    
    # Make auction.end_time aware if it's naive
    if auction.end_time.tzinfo is None:  # Check if it's naive
        auction_end_time = auction.end_time.replace(tzinfo=UTC)  # Make it aware
    else:
        auction_end_time = auction.end_time  # It's already aware

    additional_images = AdditionalImage.query.filter_by(auction_item_id=auction_id).all()
    
    # Get previous and next auction in the same category
    prev_auction = AuctionItem.query.filter(AuctionItem.id < auction_id, AuctionItem.category == auction.category).order_by(AuctionItem.id.desc()).first()
    next_auction = AuctionItem.query.filter(AuctionItem.id > auction_id, AuctionItem.category == auction.category).order_by(AuctionItem.id.asc()).first()
    
    bids = Bid.query.filter_by(auction_id=auction.id).order_by(Bid.bid_amount.desc()).all()
    current_bid = bids[0].bid_amount if bids else 0.0
    end_time_aware = auction.end_time.replace(tzinfo=timezone.utc)  # Force it to UTC
    time_left = (end_time_aware - datetime.now(timezone.utc)).total_seconds()

    print("End Time:", auction.end_time, "TZ:", auction.end_time.tzinfo)
    print("Current Time:", datetime.now(timezone.utc), "TZ:", datetime.now(timezone.utc).tzinfo)


    
     # **Convert `end_time` to UTC ISO format for JavaScript**
    auction_end_utc = auction.end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Check if auction time has expired
    if datetime.now(UTC) >= auction_end_time and auction.sale_status == 'Open':
        highest_bid = Bid.query.filter_by(auction_id=auction.id).order_by(Bid.bid_amount.desc()).first()

        if highest_bid:
            auction.sale_status = 'Sold'  # Someone placed a bid
            winner = User.query.get(highest_bid.user_id)  # Fetch the user from the User table
            flash('You have won an auction', 'success')

            # Create a notification for the winner
            notification = Notification(
                user_id=winner.id,
                message=f"Congratulations! You won the auction for {auction.title}. Please proceed with payment."
            )
            db.session.add(notification)

        else:
            auction.sale_status = 'Closed'  # No bids placed
        
        db.session.commit()

    
    if request.method == 'POST' and auction.sale_status == 'Open':
        bid_amount = float(request.form['bid_amount'])

        if bid_amount > current_bid:  # Removed membership check
            new_bid = Bid(bid_amount=bid_amount, user_id=current_user.id, auction_id=auction.id) # Corrected amount to bid_amount and added item_id
            db.session.add(new_bid)
            db.session.commit()
            flash('Bid placed successfully!', 'success')
        else:
            flash('Your bid must be higher than the current bid.', 'danger')
        return redirect(url_for('auction_details', auction_id=auction.id))
    
    # Render the details page
    return render_template('auction_details.html', auction=auction, additional_images=additional_images, prev_auction=prev_auction if prev_auction else None, next_auction=next_auction if next_auction else None, bids=bids, current_bid=current_bid, time_left=time_left, auction_end_utc=auction_end_utc, user=current_user, user_id=current_user.id, notifications=current_user.notifications)

@app.route('/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    return jsonify([{"id": n.id, "message": n.message} for n in notifications])

@app.route('/mark_notifications_read', methods=['POST'])
@login_required
def mark_notifications_read():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    return jsonify({"status": "success"})

# Define fixed distances from Nairobi (in km)
DISTANCES_FROM_NAIROBI = {
    "mombasa": 485,
    "nakuru": 160,
    "kisumu": 350,
    "eldoret": 315,
    "nyeri": 150,
    "thika": 45,
    "machakos": 63,
    "nanyuki": 195,
    "nairobi": 0,
    "kakamega": 390,
    "kericho": 290,
    "malindi": 520,
    "kitale": 380,
    "garissa": 350,
    "lodwar": 700,
    "isiolo": 320,
    "bomet": 270,
    "busia": 470,    
    "meru": 300,
    "kilifi": 490,
    "lamu": 505,
    "vihiga": 400,
    "taita taveta": 380,
    "wajir": 600,
    "mandera": 800,
    "marsabit": 560,
    "homabay": 380,
    "migori": 420,
    "nyamira": 300,
    "bomet": 270,
    "busia": 470,
}

RATE_PER_KM = 5  # Adjust based on actual rates

@app.route('/get_shipping_cost', methods=['GET'])
def get_shipping_cost():
    destination = request.args.get("destination", "").strip().lower()
    
    if destination in DISTANCES_FROM_NAIROBI:
        distance = DISTANCES_FROM_NAIROBI[destination]
        cost = distance * RATE_PER_KM
    else:
        return jsonify({"error": "Destination not found"}), 404
    
    return jsonify({"cost": cost})

# Subscribe Route
# ✅ TextBelt (Free SMS)
TEXTBELT_API_URL = "https://textbelt.com/text"
TEXTBELT_API_KEY = os.getenv("TEXTBELT_API_KEY") #Get key from .env file

# ✅ Brevo (Sendinblue) Email API
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_API_KEY = os.getenv("BREVO_API_KEY") # Get key from .env file

@app.route('/subscribe-alert', methods=['POST'])
def subscribe_alert():
    data = request.json
    method = data.get("method")
    contact = data.get("contact")

    if not method or not contact:
        return jsonify({"message": "Invalid input. Please provide a contact method and details."}), 400

    # Check if user is already subscribed
    existing_subscription = AlertSubscription.query.filter_by(contact=contact).first()
    if existing_subscription:
        return jsonify({"message": "You're already subscribed!"}), 400

    # Save subscription to database
    new_subscription = AlertSubscription(method=method, contact=contact)
    db.session.add(new_subscription)
    db.session.commit()

    # ✅ Send notification
    if method == "sms":
        response = send_sms_notification(contact)
    elif method == "email":
        response = send_email_notification(contact)
    else:
        response = {"message": "Invalid notification method."}

    return jsonify(response)

# ✅ Function to send SMS using TextBelt
def send_sms_notification(phone_number):
    payload = {
        "phone": phone_number,
        "message": "You have subscribed to auction alerts!",
        "key": "textbelt"  # Free tier key
    }
    response = requests.post(TEXTBELT_API_URL, data=payload)
    return response.json()

# ✅ Function to send Email using Brevo
def send_email_notification(email):
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": BREVO_API_KEY
    }
    payload = {
        "sender": {"name": "Auction Alerts", "email": "iankamau7036@gmail.com"},
        "to": [{"email": email}],
        "subject": "Auction Alert Subscription",
        "htmlContent": "<p>You have successfully subscribed to auction alerts.</p>"
    }
    response = requests.post(BREVO_API_URL, json=payload, headers=headers)
    return response.json()

@app.route("/unsubscribe-alert", methods=["POST"])
def unsubscribe_alert():
    contact = request.json.get("contact")  # Get user email/phone from request

    subscription = AlertSubscription.query.filter_by(contact=contact).first()
    if subscription:
        db.session.delete(subscription)
        db.session.commit()
        return jsonify({"message": "Unsubscribed successfully", "status": "unsubscribed"})
    
    return jsonify({"message": "Subscription not found", "status": "not_found"})

@app.route("/check-subscription", methods=["POST"])
def check_subscription():
    contact = request.json.get("contact")
    subscription = AlertSubscription.query.filter_by(contact=contact).first()

    if subscription:
        return jsonify({"status": "subscribed", "contact": subscription.contact})

    return jsonify({"status": "not_subscribed"})


@app.route('/auction/<int:auction_id>/upload_images', methods=['POST'])
@login_required
def upload_additional_images(auction_id):
    auction = AuctionItem.query.get_or_404(auction_id)
    images = request.files.getlist('additional_images')

    for image in images:
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            additional_image = AdditionalImage(image_filename=filename, auction_item=auction)
            db.session.add(additional_image)

    db.session.commit()
    flash("Additional images uploaded successfully!", "success")
    return redirect(url_for('view_auctions'))


@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query', '').strip()
    category = request.args.get('category', None)
    min_price = request.args.get('min_price', None, type=float)
    max_price = request.args.get('max_price', None, type=float)
    sort_by = request.args.get('sort_by', None)  # e.g., 'ending_soon'
    
    # Base query
    auctions = AuctionItem.query
    
    # Filter by query keyword
    if query:
        auctions = auctions.filter(AuctionItem.title.ilike(f'%{query}%'))
    
    # Filter by category
    if category:
        auctions = auctions.filter(AuctionItem.category == category)
    
    # Filter by price range
    if min_price is not None:
        auctions = auctions.filter(AuctionItem.starting_price >= min_price)
    if max_price is not None:
        auctions = auctions.filter(AuctionItem.starting_price <= max_price)
    
    # Sort results
    if sort_by == 'ending_soon':
        auctions = auctions.order_by(AuctionItem.end_time.asc())
    elif sort_by == 'price_low_to_high':
        auctions = auctions.order_by(AuctionItem.starting_price.asc())
    elif sort_by == 'price_high_to_low':
        auctions = auctions.order_by(AuctionItem.starting_price.desc())
    
    # Execute query
    auctions = auctions.all()
    
    return render_template('search_results.html', auctions=auctions)


@app.route('/autocomplete', methods=['GET'])
@login_required
def autocomplete():
    term = request.args.get('term', '').strip()
    suggestions = AuctionItem.query.filter(AuctionItem.title.ilike(f'%{term}%')).limit(5).all()
    return jsonify([auction.title for auction in suggestions])


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Check if username already exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        # Create new user (non-admin)
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(username=form.username.data, password=hashed_password, is_admin=False)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form, is_admin=False)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/')
@login_required
def home():
    featured_items = AuctionItem.query.filter_by(category='Featured').all()
    expired_auctions = AuctionItem.query.filter(AuctionItem.end_time < datetime.utcnow()).all()
    return render_template('home.html', featured_items=featured_items, expired_auctions=expired_auctions, user= current_user)

# Other routes forbidding, etc.
def get_bid_status(user_id, auction):
    highest_bid = Bid.query.filter_by(auction_id=auction.id).order_by(Bid.bid_amount.desc()).first()
    if highest_bid and highest_bid.user_id == user_id:
        return "Winning"
    return "Losing"

@app.route('/bid_history')
@login_required
def bid_history():
    # Fetch all bids by the user
    user_bids = Bid.query.filter_by(user_id=current_user.id).join(AuctionItem).all()

    current_bids = []
    winning_bids = []
    losing_bids = []
    bid_history = []

    for bid in user_bids:
        auction = db.session.get(AuctionItem, bid.auction_id)
        status = get_bid_status(current_user.id, auction)
        
        bid_info = {
            "item": auction.title,
            "bid_amount": bid.bid_amount,
            "auction_status": auction.sale_status,
            "bid_status": status,
            "auction_end": auction.end_time
        }
        
        if auction.sale_status == "Open":
            if status == "Winning":
                winning_bids.append(bid_info)
            else:
                losing_bids.append(bid_info)
            current_bids.append(bid_info)
        else:
            bid_info["bid_status"] = "Won" if status == "Winning" else "Lost"
            bid_history.append(bid_info)
    
    return render_template('bid_history.html', current_bids=current_bids, winning_bids=winning_bids, 
                           losing_bids=losing_bids, bid_history=bid_history)

if __name__ == '__main__':
    # Use app.app_context() to create tables
    with app.app_context():
        #db.drop_all()
        db.create_all()  # This ensures it works within the application context
        
        # Check for admin existence
        if not User.query.filter_by(is_admin=True).first():
            print("No admin users found. Visit /admin/register to create the first admin account.")

    app.run(debug=True)