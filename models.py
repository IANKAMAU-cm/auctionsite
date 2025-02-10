from database import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class AuctionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    starting_price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(100), nullable=True)
    end_time = db.Column(db.DateTime, nullable=False)
    bids = db.relationship('Bid', backref='auction_item', lazy=True)
    category = db.Column(db.String(50), nullable=False)  # New field for category
    additional_images = db.relationship('AdditionalImage', back_populates='auction_item', cascade="all, delete-orphan")
    
    # New fields
    serial_number = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(50), nullable=True)
    year_of_manufacture = db.Column(db.String(4), nullable=True)
    color = db.Column(db.String(30), nullable=True)
    primary_damage = db.Column(db.String(50), nullable=True)
    secondary_damage = db.Column(db.String(50), nullable=True)
    VIN = db.Column(db.String(17), nullable=True)
    odometer = db.Column(db.Integer, nullable=True)
    working = db.Column(db.String(10), nullable=True)  # Yes/No/Not Applicable
    sale_status = db.Column(db.String(20), default='Open')  # Open, Closed, or Sold
    
class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    auction_id = db.Column(db.Integer, db.ForeignKey('auction_item.id'), nullable=False)
    bid_amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    
class AdditionalImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(200), nullable=False)
    auction_item_id = db.Column(db.Integer, db.ForeignKey('auction_item.id'), nullable=False)

    # Relationship back to the auction item
    auction_item = db.relationship('AuctionItem', back_populates='additional_images')
    
    
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))
    

