from models.base import db


class Toot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mastodon_id = db.Column(db.Integer)
    creation_date = db.Column(db.DateTime)
    sensitive = db.Column(db.Boolean)
    content = db.Column(db.String(4095))
    url = db.Column(db.String(4095))
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    instance_id = db.Column(db.Integer, db.ForeignKey('instance.id'))

    # def __init__(self, id, mastodon_id, creation_date, sensitive, account_id,
    #              content, url, instance_id):
    #     self.id = id
    #     self.mastodon_id = mastodon_id
    #     self.creation_date = creation_date
    #     self.sensitive = sensitive
    #     self.account_id = account_id
    #     self.conten = content
    #     self.url = url
    #     self.instance_id = instance_id
