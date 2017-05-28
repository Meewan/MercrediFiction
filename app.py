from os import environ, path
from datetime import datetime
from hashlib import md5

from flask import Flask, render_template, request, send_from_directory, redirect
from sqlalchemy import desc
from flask_sqlalchemy import SQLAlchemy
from ebooklib import epub

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

    toots, count, count_all = get_toots(offset, limit)
    accounts = Account.query.order_by(Account.username)
    instances = Instance.query.order_by(Instance.domain)
    blacklist_status = True if request.args.get('blacklisted', None) else False

    if request.args.get('blacklisted') != 'ignore':
        accounts = accounts.filter(Account.blacklisted == blacklist_status)
        instances = instances.filter(Instance.blacklisted == blacklist_status)

    pagination = {'page': page + 1,
                  'limit': limit}
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

    pagination['page_count'] = int(count_all / limit) + 1

    return render_template('index.html',
                           toots=toots,
                           accounts=accounts,
                           instances=instances,
                           pagination=pagination)

@app.route('/epub')
def create_epub():
    accounts = Account.query.order_by(Account.username)
    toots = Toot.query.order_by(Toot.creation_date)
    book = epub.EpubBook()

    # add metadata
    book.set_identifier('mercredi-fiction')
    book.set_title('#MercrediFiction')
    book.set_language('fr')

    for account in accounts:
        book.add_author(account.username)

    chapter = epub.EpubHtml(title='Toutes les histoires', file_name='index.xhtml', lang='fr')
    chapter.content = render_template('epub.html', toots=toots)
    book.add_item(chapter)

    book.toc = (epub.Link('index.xhtml', 'Toutes les histoires', 'histoires'), )

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    book.spine = ['nav', chapter]

    epub_path = path.join('static', 'mercredi-fiction.epub')
    epub.write_epub(epub_path, book, {})
    return redirect(epub_path)

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


def get_toots(offset, limit):
    toots = Toot.query
    joined_account = False
    joined_instance = False
    if request.args.get('author', None):
        joined_account = True
        toots = toots.join(Account, Toot.account)
        toots = toots.filter(Account.username == request.args.get('author'))

    if request.args.get('instance', None):
        joined_instance = True
        toots = toots.join(Instance, Toot.instance)
        toots = toots.filter(Instance.domain == request.args.get('instance'))

    if request.args.get('from_date', None):
        try:
            date = datetime.strptime(request.args.get('from_date'), "%Y%m%d")
            toots = toots.filter(Toot.creation_date >= date)
        except ValueError:
            pass

    if request.args.get('to_date', None):
        try:
            date = datetime.strptime(request.args.get('to_date'), "%Y%m%d")
            toots = toots.filter(Toot.creation_date <= date)
        except ValueError:
            pass

    if request.args.get('search'):
        if request.args.get('fullword'):
            search = "(^| )%s( |$)" % (request.args.get("search"),)
            toots = toots.filter(Toot.content.op('REGEXP')(search))
        else:
            search_string = "%" + request.args.get("search") + "%"
            toots = toots.filter(Toot.content.like(search_string))

    blacklist_status = True if request.args.get('blacklisted', None) else False

    if request.args.get('blacklisted') != 'ignore':
        toots = toots.filter(Toot.blacklisted == blacklist_status)
        if not joined_account:
            toots = toots.join(Account, Toot.account)
        toots = toots.filter(Account.blacklisted == blacklist_status)
        if not joined_instance:
            toots = toots.join(Instance, Toot.instance)
        toots = toots.filter(Account.blacklisted == blacklist_status)

    toots = toots.order_by(desc(Toot.creation_date))
    count_all = toots.count()
    toots = toots.offset(offset).limit(limit)
    count = toots.count()
    toots = toots.all()

    return toots, count, count_all
