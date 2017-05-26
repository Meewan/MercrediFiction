from app import db


class Toot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mastodon_id = db.Column(db.Integer)
    creation_date = db.Column(db.DateTime)
    sensitive = db.Column(db.Boolean)
    content = db.Column(db.String(4095))
    url = db.Column(db.String(4095))
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    instance_id = db.Column(db.Integer, db.ForeignKey('instance.id'))
    blacklisted = db.Column(db.Boolean)


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mastodon_id = db.Column(db.Integer)
    username = db.Column(db.String(1024))
    display_name = db.Column(db.String(4095))
    creation_date = db.Column(db.DateTime)
    note = db.Column(db.String(4095))
    url = db.Column(db.String(4095))
    avatar = db.Column(db.String(4095))
    instance_id = db.Column(db.Integer, db.ForeignKey('instance.id'))
    toots = db.relationship('Toot', backref='account', lazy='dynamic')
    blacklisted = db.Column(db.Boolean)


class Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creation_date = db.Column(db.DateTime)
    domain = db.Column(db.String(1024))
    toots = db.relationship('Toot', backref='instance', lazy='dynamic')
    accounts = db.relationship('Account', backref='instance', lazy='dynamic')
    lock = db.Column(db.Boolean)
    blacklisted = db.Column(db.Boolean)


class Telemetry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creation_date = db.Column(db.DateTime)
    ip = db.Column(db.String(32))
    referrer = db.Column(db.String(4096))


def save(obj):
    db.session.add(obj)
    db.session.commit()
