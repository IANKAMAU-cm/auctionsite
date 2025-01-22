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
    
class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('auction_item.id'), nullable=False)
    bid_amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    
class AdditionalImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(200), nullable=False)
    auction_item_id = db.Column(db.Integer, db.ForeignKey('auction_item.id'), nullable=False)

    # Relationship back to the auction item
    auction_item = db.relationship('AuctionItem', back_populates='additional_images')