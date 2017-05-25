from flask_sqlalchemy import SQLAlchemy

from app import app

db = SQLAlchemy(app)


def save(obj):
    db.session.add(obj)
    db.session.commit()
