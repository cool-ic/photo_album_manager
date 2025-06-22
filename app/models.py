from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

db = SQLAlchemy()

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filepath = db.Column(db.String(1024), unique=True, nullable=False)
    org_path = db.Column(db.String(1024), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    capture_time = db.Column(db.DateTime, default=datetime(1999, 1, 1, 0, 0, 0))
    modification_time = db.Column(db.DateTime, nullable=False)
    filesize = db.Column(db.Integer, nullable=False) # size in bytes
    media_type = db.Column(db.String(50), nullable=False) # 'image' or 'video'
    is_accessible = db.Column(db.Boolean, default=True, nullable=False, server_default='1') # True if part of current ORG_PATHS and exists

    tags = db.relationship('Tag', secondary='media_tag', backref=db.backref('media_items', lazy='dynamic'))

    def __repr__(self):
        return f'<Media {self.filename}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<Tag {self.name}>'

# Association table for Many-to-Many relationship between Media and Tag
media_tag = db.Table('media_tag',
    db.Column('media_id', db.Integer, db.ForeignKey('media.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

def init_db(app):
    # Define the database URI.
    # The database file will be created inside the 'data' directory.
    # app.instance_path will be /app/photo_album_manager/photo_album_manager/instance
    db_path = os.path.join(app.instance_path, '..', 'data', 'photo_album.sqlite')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Ensure the 'data' directory exists.
    # os.path.join(app.instance_path, '..', 'data') correctly navigates to
    # /app/photo_album_manager/photo_album_manager/data
    data_dir = os.path.dirname(db_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created directory: {data_dir}")

    print(f"Database will be created at: {db_path}")

    db.init_app(app)
    with app.app_context():
        db.create_all()
    print("Database initialized and tables created.")
