from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
import os
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
app.config['SECRET_KEY'] = 'your_secret_key'

# Initialize database with app
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Import models and forms
from models import User, AuctionItem, Bid
from forms import LoginForm, RegisterForm #AuctionForm, BidForm


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
        end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
        
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
                                   starting_price=starting_price, image=image_path, end_time=end_time)
        db.session.add(auction_item)
        db.session.commit()
        flash('Auction added successfully!')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_auction.html')

@app.route('/admin/edit-auction/<int:auction_id>', methods=['GET', 'POST'])
@login_required
def edit_auction(auction_id):
    if not current_user.is_admin:
        flash('Unauthorized access!')
        return redirect(url_for('home'))
    auction_item = AuctionItem.query.get_or_404(auction_id)
    if request.method == 'POST':
        auction_item.title = request.form['title']
        auction_item.description = request.form['description']
        auction_item.starting_price = float(request.form['starting_price'])
        auction_item.end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
        
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
    return render_template('edit_auction.html', auction_item=auction_item)

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
    return User.query.get(int(user_id))


@app.route('/')
@login_required
def home():
    auctions = AuctionItem.query.filter(AuctionItem.end_time > datetime.now()).all()
    expired_auctions = AuctionItem.query.filter(AuctionItem.end_time < datetime.utcnow()).all()
    return render_template('home.html', auctions=auctions, expired_auctions=expired_auctions, user= current_user)

# Other routes for login, registration, bidding, etc.

if __name__ == '__main__':
    # Use app.app_context() to create tables
    with app.app_context():
        #db.drop_all()
        db.create_all()  # This ensures it works within the application context
        
        # Check for admin existence
        if not User.query.filter_by(is_admin=True).first():
            print("No admin users found. Visit /admin/register to create the first admin account.")

    app.run(debug=True)