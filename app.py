from os import environ, path, listdir, remove
from time import time
from datetime import datetime
from hashlib import md5

from flask import Flask, render_template, request, send_from_directory
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
def index_page():
    if request.args.get('epub'):
        return create_epub()
    else:
        return create_page()


def create_page():
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


def create_epub():
    toots, _, _ = get_toots()
    accounts, _, _ = get_accounts()
    book = epub.EpubBook()

    # add metadata
    book.set_identifier('mercredi-fiction')
    book.set_title('#MercrediFiction')
    book.set_language('fr')

    for account in accounts:
        book.add_author(account.username)

    chapter = epub.EpubHtml(title='Toutes les histoires',
                            file_name='index.xhtml',
                            lang='fr')
    chapter.content = render_template('epub.html', toots=toots)
    book.add_item(chapter)

    book.toc = (epub.Link('index.xhtml', 'Toutes les histoires', 'histoires'),)

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    book.spine = ['nav', chapter]

    clean_epub_directory()
    epub_name = str(time()) + '.epub'
    epub_path = path.join(config.EPUB_DIRECTORY, epub_name)
    epub.write_epub(epub_path, book)
    response = send_from_directory(config.EPUB_DIRECTORY, epub_name)
    response.headers['Content-Disposition'] = 'attachment;filename="mercredifiction.epub"'
    return response


def get_toots(offset=None, limit=None):
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
            joined_account = True
            toots = toots.join(Account, Toot.account)
        toots = toots.filter(Account.blacklisted == blacklist_status)
        if not joined_instance:
            joined_instance = True
            toots = toots.join(Instance, Toot.instance)
        toots = toots.filter(Account.blacklisted == blacklist_status)

    toots = toots.order_by(desc(Toot.creation_date))
    count_all = toots.count()
    if offset:
        toots = toots.offset(offset)
    if limit:
        toots = toots.limit(limit)
    count = toots.count()
    toots = toots.all()

    return toots, count, count_all


def get_accounts():
    accounts = Account.query.join(Toot, Account.toots)
    joined_instance = False

    if request.args.get('author', None):
        accounts = accounts.filter(Account.username == request.args['author'])

    if request.args.get('instance', None):
        joined_instance = True
        accounts = accounts.join(Instance, Account.instance)
        accounts = accounts.filter(
            Instance.domain == request.args.get('instance')
        )

    if request.args.get('from_date', None):
        try:
            date = datetime.strptime(request.args.get('from_date'), "%Y%m%d")
            accounts = accounts.filter(Toot.creation_date >= date)
        except ValueError:
            pass

    if request.args.get('to_date', None):
        try:
            date = datetime.strptime(request.args.get('to_date'), "%Y%m%d")
            accounts = accounts.filter(Toot.creation_date <= date)
        except ValueError:
            pass

    if request.args.get('search'):
        if request.args.get('fullword'):
            search = "(^| )%s( |$)" % (request.args.get("search"),)
            accounts = accounts.filter(Toot.content.op('REGEXP')(search))
        else:
            search_string = "%" + request.args.get("search") + "%"
            accounts = accounts.filter(Toot.content.like(search_string))

    blacklist_status = True if request.args.get('blacklisted', None) else False

    if request.args.get('blacklisted') != 'ignore':
        accounts = accounts.filter(Toot.blacklisted == blacklist_status)
        accounts = accounts.filter(Account.blacklisted == blacklist_status)
        if not joined_instance:
            accounts = accounts.join(Instance, Toot.instance)
        accounts = accounts.filter(Account.blacklisted == blacklist_status)

    accounts = accounts.order_by(Account.username)
    count_all = accounts.count()
    count = accounts.count()
    accounts = accounts.all()

    return accounts, count, count_all


def clean_epub_directory():
    epubs = listdir(config.EPUB_DIRECTORY)
    if len(epubs) <= config.MAX_EPUB:
        return

    epubs.sort()

    number_to_delete = len(epubs) - config.MAX_EPUB + 2
    deleted = 0
    for t in epubs:
        f = path.join(config.EPUB_DIRECTORY, t)
        if not path.isfile(f):
            continue
        if deleted >= number_to_delete:
            break
        try:
            remove(f)
            deleted += 1
        except OSError:
            pass
