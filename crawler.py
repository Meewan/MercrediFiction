import re
import json
from datetime import datetime
from urlparse import urlparse
from threading import Thread

import requests
from requests.exceptions import ConnectionError, Timeout
from sqlalchemy import desc

from models.toot import Toot
from models.instance import Instance
from models.account import Account
from models.base import save
from const import GET_TAG, MAX_ID, SINCE_ID, TOOT_LIMIT
from config import TAGS


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
                           content=filter_content(toot['content']),
                           instance=instance)
            save(db_toot)


def filter_content(content):
    # remove <p> tags
    result = re.sub("<p>(.*)</p>", r"\1", content)
    # replace links by url bbcode
    result = re.sub("<a href=(?P<quote>'|\")(.*?)(?P=quote)>(.*?)</a>",
                    r"""[url="\2"]\3[/url]""", result)
    # remove span 3 times to be sure to remove all span
    result = re.sub("<span(.*?)>(.*?)</span>", r"\2", result)
    result = re.sub("<span(.*?)>(.*?)</span>", r"\2", result)
    result = re.sub("<span(.*?)>(.*?)</span>", r"\2", result)
    return result


def save_account(instance, content):
    username = filter_content(content['username'])
    domain = instance.domain
    acct = "@" + username + "@" + domain
    if Account.query.filter_by(username=acct).count() != 0:
        return Account.query.filter_by(username=acct).first()
    else:
        creation_date = datetime.strptime(content['created_at'],
                                          "%Y-%m-%dT%H:%M:%S.%fZ")
        account = Account(mastodon_id=content['id'],
                          username=acct,
                          display_name=filter_content(content['display_name']),
                          creation_date=creation_date,
                          note=filter_content(content['note']),
                          url=content['url'],
                          avatar=content['avatar'],
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
