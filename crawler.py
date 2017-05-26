import re
import json
from os import environ
from datetime import datetime
from urlparse import urlparse
from threading import Thread

import requests
from requests.exceptions import ConnectionError, Timeout
from html2text import HTML2Text
from sqlalchemy import desc

environ['MercredifictionCrawler'] = 'MercredifictionCrawler'


from models import Toot, Account, Instance, save
from const import GET_TAG, MAX_ID, SINCE_ID, TOOT_LIMIT
from config import TAGS


# from django validator
URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...  # noqa
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

USERNAME_REGEX = re.compile('''^[a-zA-Z0-9_]+$''')


def main():
    instances = Instance.query.all()

    # creating threads
    threads = []
    for instance in instances:
        threads.append(Thread(target=crawl,
                              args=(instance.id, )))

    # launching threads
    for t in threads:
        t.start()

    # waiting threads to end
    for t in threads:
        t.join()


def crawl(instance_id):
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance.lock:
        return
    instance.lock = True
    save(instance)
    try:
        toots_query = Toot.query.filter_by(instance_id=instance_id)
        toots_count = toots_query.count()
        if toots_count == 0:
            since_id = None
        else:
            last_toot = toots_query.order_by(desc(Toot.id)).first()
            since_id = last_toot.id

        get_toots(instance, since_id)
    finally:
        instance.lock = False
        save(instance)


def get_toots(instance, since_id=None, max_id=None):
    last_query_len = int(TOOT_LIMIT)
    arguments = {'domain': instance.domain, "tag": TAGS}
    while last_query_len == int(TOOT_LIMIT):
        query = GET_TAG
        if since_id:
            query += SINCE_ID
            arguments['since_id'] = since_id
        if max_id:
            query += MAX_ID
            arguments['max_id'] = max_id

        try:
            result = requests.get(query % arguments, timeout=120)
        except (ConnectionError, Timeout):
            break
        if result.status_code != 200:
            break

        content = json.loads(result.content)
        last_query_len = len(content)
        for toot in content:
            max_id = toot['id'] if max_id is None else min(max_id, toot['id'])
            toot_domain = urlparse(toot['url']).netloc
            if toot_domain != instance.domain:
                add_domain_to_db(toot_domain)
                continue

            toot_count = Toot.query.filter_by(mastodon_id=toot['id'],
                                              instance_id=instance.id).count()
            if toot_count != 0:
                last_query_len = None
                break

            creation_date = datetime.strptime(toot['created_at'],
                                              "%Y-%m-%dT%H:%M:%S.%fZ")
            account = save_account(instance, toot['account'])
            db_toot = Toot(mastodon_id=toot['id'],
                           creation_date=creation_date,
                           sensitive=toot['sensitive'],
                           account=account,
                           content=to_text(toot['content']),
                           instance=instance,
                           url=validate_url(toot['url']))
            save(db_toot)


def to_text(html):
    parser = HTML2Text()
    parser.wrap_links = False
    parser.skip_internal_links = True
    parser.inline_links = True
    parser.ignore_anchors = True
    parser.ignore_images = True
    parser.ignore_emphasis = True
    parser.ignore_links = True
    text = parser.handle(html)
    text = text.replace('\n', '<br/>')
    text = text.replace('\\', '')
    return text


def validate_url(url):
    if URL_REGEX.match(url):
        return url
    else:
        return ''


def save_account(instance, content):
    username = content['username']
    if not USERNAME_REGEX.match(username):
        username = '[invalid_username]'
    domain = instance.domain
    acct = "@" + username + "@" + domain
    if Account.query.filter_by(username=acct).count() != 0:
        return Account.query.filter_by(username=acct).first()
    else:
        creation_date = datetime.strptime(content['created_at'],
                                          "%Y-%m-%dT%H:%M:%S.%fZ")
        account = Account(mastodon_id=content['id'],
                          username=acct,
                          display_name=to_text(content['display_name']),
                          creation_date=creation_date,
                          note=to_text(content['note']),
                          url=validate_url(content['url']),
                          avatar=validate_url(content['avatar']),
                          instance=instance)
        save(account)
        return account


def add_domain_to_db(domain):
    if not Instance.query.filter_by(domain=domain).count():
        instance = Instance(creation_date=datetime.now(),
                            domain=domain,
                            lock=False)
        save(instance)


if __name__ == "__main__":
    main()
