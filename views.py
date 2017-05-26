from flask import render_template
from sqlalchemy import desc


from app import app, db

from models.toot import Toot
from models.account import Account
from models.instance import Instance


@app.route('/')
def show_entries():
    query = db.query(Toot, Account)
    query = query.join(Account.id, Toot.account_id)
    query = query.order_by(desc(Toot.creation_date))
    query = query.limit(10)
    return render_template('index.html', toots=query.all())
