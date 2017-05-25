from models.base import db


class Account(db.Model):
    from models.toot import Toot
    id = db.Column(db.Integer, primary_key=True)
    mastodon_id = db.Column(db.Integer)
    username = db.Column(db.String(1024))
    display_name = db.Column(db.String(4095))
    creation_date = db.Column(db.DateTime)
    note = db.Column(db.String(4095))
    url = db.Column(db.String(4095))
    avatar = db.Column(db.String(4095))
    toots = db.relationship('Toot', backref='account', lazy='dynamic')
    instance_id = db.Column(db.Integer, db.ForeignKey('instance.id'))

    # def __init__(self, id, mastodon_id, username, display_name, creation_date, note, url,
    #              avatar, toots, instance_id):
    #     self.id = id
    #     self.username = username
    #     self.display_nam = display_name
    #     self.creation_date = creation_date
    #     self.note = note
    #     self.url = url
    #     self.avatar = avatar
    #     self.toots = toots
    #     self.instance_id = instance_id
