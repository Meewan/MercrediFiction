from models.base import db


class Instance(db.Model):
    from models.toot import Toot
    from models.account import Account
    id = db.Column(db.Integer, primary_key=True)
    creation_date = db.Column(db.DateTime)
    domain = db.Column(db.String(1024))
    toots = db.relationship('Toot', backref='instance', lazy='dynamic')
    accounts = db.relationship('Account', backref='instance', lazy='dynamic')
    lock = db.Column(db.Boolean)

    # def __init__(self, id, creation_date, domain, toots, accounts):
    #     self.id = id
    #     self.creation_date = creation_date
    #     self.domain = domain
    #     self.toots = toots
    #     self.accounts = accounts
