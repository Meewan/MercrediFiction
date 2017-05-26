from os import environ
from datetime import datetime
from hashlib import md5

from flask import Flask, render_template, request
from sqlalchemy import desc
from flask_sqlalchemy import SQLAlchemy

import config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

if not environ.get('MercredifictionCrawler'):
    from models import Toot, Account, Instance, Telemetry, save


def telemetry(function):
    def _wrapper(*args, **kwargs):
        telemetry = Telemetry(referrer=request.referrer,
                              ip=md5(request.remote_addr).hexdigest(),
                              creation_date=datetime.now())
        save(telemetry)
        return function(*args, **kwargs)
    return _wrapper


@app.route('/')
@telemetry
def show_entries():
    page = int(request.args.get("page", "0"))
    limit = int(request.args.get("limit", "10"))
    offset = page * limit

    toots, count = get_toots(offset, limit)

    pagination = {'page': page + 1}
    pagination['next'] = "/?page=%s&" % (page + 1)
    pagination['previous'] = "/?page=%s&" % (page - 1)
    for key, value in request.args.iteritems():
        if not key == "page":
            pagination['next'] += "&%s=%s" % (key, value)
            pagination['previous'] += "&%s=%s" % (key, value)

    if count < limit:
        pagination.pop('next')
    if page == 0:
        pagination.pop('previous')

    return render_template('index.html', toots=toots, pagination=pagination)


def get_toots(offset, limit):
    toots = Toot.query
    if 'author' in request.args:
        toots = toots.join(Account, Toot.account)
        toots = toots.filter(Account.username == request.args.get('author'))

    if 'instance' in request.args:
        toots = toots.join(Instance, Toot.instance)
        toots = toots.filter(Instance.domain == request.args.get('instance'))

    if 'from_date' in request.args:
        try:
            date = datetime.strptime(request.args.get('from_date'), "%Y%m%d")
            toots = toots.filter(Toot.creation_date >= date)
        except ValueError:
            pass

    if 'to_date' in request.args:
        try:
            date = datetime.strptime(request.args.get('to_date'), "%Y%m%d")
            toots = toots.filter(Toot.creation_date <= date)
        except ValueError:
            pass

    if 'search' in request.args:
        search_string = "%" + request.args.get("search") + "%"
        toots = toots.filter(Toot.content.like(search_string))

    toots = toots.order_by(desc(Toot.creation_date))
    toots = toots.offset(offset).limit(limit)
    count = toots.count()
    toots = toots.all()

    return toots, count
