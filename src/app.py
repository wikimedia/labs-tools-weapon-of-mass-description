# -*- coding: utf-8 -*-
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

import flask
import os
import pymysql
import yaml
import simplejson as json
import requests
from flask import request, jsonify, make_response, render_template
import mwoauth
from requests_oauthlib import OAuth1
import random
import toolforge
from flask_jsonlocale import Locales

app = flask.Flask(__name__, static_folder='../static')
application = app

locales = Locales(app)

ua = "Weapon of Mass Description (https://tools.wmflabs.org/weapon-of-mass-description; martin.urbanec@wikimedia.cz"
requests.utils.default_user_agent = lambda: ua

__dir__ = os.path.dirname(__file__)
app.config.update(yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))

key = app.config['CONSUMER_KEY']
secret = app.config['CONSUMER_SECRET']

def wdconnect():
    return toolforge.connect('wikidatawiki')

def tconnect():
    return pymysql.connect(
            database=app.config['DB_NAME'],
            host='tools.db.svc.eqiad.wmflabs',
            read_default_file=os.path.expanduser("~/replica.my.cnf"),
            charset='utf8mb4',
    )

def logged():
    return flask.session.get('username') is not None

def getusername():
    return flask.session.get('username')

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

@app.route('/')
def index():
    username = flask.session.get('username')
    if username is not None:
        return render_template('tool.html', logged=logged(),username=getusername(), settings=getsettings())
    else:
        return render_template('login.html', logged=logged(), username=getusername())

@app.route('/settings')
def settingspage():
    if logged():
        return render_template('settings.html', logged=logged(), username=getusername(), settings=getsettings())
    else:
        return render_template('login.html', logged=logged(), username=getusername())

@app.route('/api-username')
def apiusername():
    response = {
        'status': 'ok',
        'username': getusername()
    }
    return jsonify(response)

@app.route('/users')
def users():
    conn = wdconnect()
    with conn.cursor() as cur:
        sql = 'select rev_user_text, count(*) from change_tag join revision on ct_rev_id=rev_id where ct_tag="OAuth CID: 998" and rev_user>0 group by rev_user order by count(*) desc;'
        cur.execute(sql)
        data = cur.fetchall()
    users = []
    for user in data:
        rowres = []
        for item in user:
            if type(item) == type(b'a'):
                rowres.append(item.decode('utf-8'))
            else:
                rowres.append(item)
        users.append(rowres)
    with conn.cursor() as cur:
        sql = 'select count(*) from change_tag join revision on ct_rev_id=rev_id where ct_tag="OAuth CID: 998" and rev_user>0;'
        cur.execute(sql)
        data = cur.fetchall()
    total = data[0][0]
    return flask.render_template('users.html', users=users, total=total, logged=logged(), username=getusername())

@app.route('/api-suggestitems')
def suggestitems():
    wiki = request.args.get('wiki')
    num = request.args.get('num')
    if wiki is None or num is None:
        response = {
            'status': 'error',
            'errorcode': 'mustpassparams'
        }
        return make_response(jsonify(response), 400)
    num = int(num)
    url = 'https://%s.wikipedia.org/w/api.php' % (wiki.replace('wiki', ''), )
    params = {
        "action": "query",
        "format": "json",
        "meta": "siteinfo"
    }
    r = requests.get(url, params=params)
    fallbacklang = r.json()['query']['general']['fallback'][0]['code']
    conn = toolforge.connect(wiki)
    with conn.cursor() as cur:
        sql = "SELECT DISTINCT eu_entity_id FROM wbc_entity_usage WHERE eu_aspect = 'L.%s' AND eu_entity_id LIKE 'Q%%' LIMIT %d" % (fallbacklang, num*50)
        rows = cur.execute(sql)
        if rows/2<num:
            num = None
        data = cur.fetchall()
        items = []
        for row in data:
            items.append(row[0])
    nums = []
    if num is not None:
        for i in range(0, num):
            while True:
                r = random.randint(0, len(items)-1)
                if r not in nums:
                    nums.append(r)
                    break
        itemspass = []
        for num in nums:
            itemspass.append(items[num])
    else:
        itemspass = items
    response = {
        'status': 'ok',
        'items': itemspass
    }
    return jsonify(response)


@app.route('/api-item')
def apiitem():
    itemid = request.args.get('item')
    langs = request.args.get('langs')
    lang = request.args.get('lang')
    if not lang:
        lang = 'cs'
    if not langs:
        langs = "|".join(['en', 'de', 'fr'])
    params = {
        "action": "wbgetentities",
        "format": "json",
        "ids": itemid,
        "redirects": "yes",
        "props": "sitelinks|labels|descriptions",
        "languages": langs
    }
    r = requests.get(app.config['API_MWURI'], params=params)
    data = r.json()['entities']
    response = {
        'status': 'ok'
    }
    items = []
    for entity in data:
        dataDescribed = described(entity, lang)
        if dataDescribed['describedDescription'] and dataDescribed['describedLabels']:
            continue
        labels = []
        for label in data[entity]['labels']:
            labels.append(data[entity]['labels'][label])
        descriptions = []
        for description in data[entity]['descriptions']:
            descriptions.append(data[entity]['descriptions'][description])
        items.append({
            'labels': labels,
            'descriptions': descriptions,
            'enableDescription': not dataDescribed['describedDescription'],
            'enableLabel': not dataDescribed['describedLabels'],
            'qid': entity,
        })
    response['items'] = items
    return jsonify(response)

def described(qid, lang):
    payload = {
        "action": "wbgetentities",
        "format": "json",
        "ids": qid,
        "props": "labels|descriptions",
        "languages": lang
    }
    r = requests.get(app.config['API_MWURI'], params=payload)
    data = r.json()['entities'][qid]
    response = {
        'status': 'ok',
        'qid': qid,
        'lang': lang,
        'describedLabels': lang in data['labels'],
        'describedDescription': lang in data['descriptions']
    }
    return response

@app.route('/api-described')
def apidescribed():
    qid = request.args.get('qid')
    lang = request.args.get('lang')
    return jsonify(described(qid, lang))

def edit(qid, language, label, description):
    request_token_secret = flask.session.get('request_token_secret', None)
    request_token_key = flask.session.get('request_token_key', None)
    auth = OAuth1(key, secret, request_token_key, request_token_secret)
    dataDescribed = described(qid, language)
    if label != '' and not dataDescribed['describedLabels']:
        payload = {
            "action": "query",
            "format": "json",
            "meta": "tokens",
            "type": "csrf"
        }
        r = requests.get(
            app.config['API_MWURI'],
            params=payload,
            auth=auth
        )
        token = r.json()['query']['tokens']['csrftoken']
        payload = {
            "action": "wbsetlabel",
            "format": "json",
            "id": qid,
            "token": token,
            "language": language,
            "value": label
        }
        r = requests.post(
            app.config['API_MWURI'],
            data=payload,
            auth=auth
        )
        data = r.json()
    if description != '' and not dataDescribed['describedDescription']:
        payload = {
            "action": "query",
            "format": "json",
            "meta": "tokens",
            "type": "csrf"
        }
        r = requests.get(
            app.config['API_MWURI'],
            params=payload,
            auth=auth
        )
        token = r.json()['query']['tokens']['csrftoken']
        payload = {
            "action": "wbsetdescription",
            "format": "json",
            "id": qid,
            "token": token,
            "language": language,
            "value": description
        }
        r = requests.post(
            app.config['API_MWURI'],
            data=payload,
            auth=auth
        )
        data = r.json()
    return True

@app.route('/api-edit', methods=['post'])
def apiedit():
    data = request.get_json()
    languages = langs()['langs']
    langcodes = []
    for item in languages:
        langcodes.append(item['code'])
    for item in data:
        if 'label' not in item or 'description' not in item or 'lang' not in item or 'qid' not in item:
            if 'qid' in item:
                id = item['qid']
            else:
                id = 'n-a'
            response = {
                'status': 'error',
                'errorcode': 'mustpassparams',
                'qid': id
            }
            return make_response(jsonify(response), 400)
        if item['lang'] not in langcodes:
            response = {
                'status': 'error',
                'errorcode': 'nonexistentlang',
                'id': image['id']
            }
            return make_response(jsonify(response), 400)
        res = edit(item['qid'], item['lang'], item['label'], item['description'])
        if not res:
            response = {
                'status': 'error',
                'errorcode': 'unknown'
            }
            return make_response(jsonify(response), 500)
    response = {'status': 'ok'}
    return jsonify(response)

def langs():
    params = {
        "action": "sitematrix",
        "format": "json",
        "smtype": "language",
        "smstate": "all",
        "smlangprop": "code|localname",
        "smlimit": "max"
    }
    r = requests.get(app.config['API_MWURI'], params=params)
    data = r.json()
    langs = []
    for key in data['sitematrix'].keys():
        if key != 'count':
            langs.append({
                'code': data['sitematrix'][key]['code'],
                'name': data['sitematrix'][key]['localname']
            })
    res = {
        'status': 'ok',
        'langs': sorted(langs, key=lambda k: k['name'])
    }
    return res

@app.route('/api-langs')
def apilangs():
    return jsonify(langs())

def blocked():
    username = flask.session.get('username')
    if username is None:
        response = {
            'status': 'error',
            'errorcode': 'anonymoususe'
        }
        return response
    payload = {
        "action": "query",
        "format": "json",
        "list": "users",
        "usprop": "blockinfo",
        "ususers": username
    }
    r = requests.get(app.config['API_MWURI'], params=payload)
    data = r.json()['query']['users'][0]
    response = {
        'status': 'ok',
        'blockstatus': 'blockid' in data
    }
    if response['blockstatus']:
        response['blockdata'] = {
            'blockedby': data['blockedby'],
            'blockexpiry': data['blockexpiry'],
            'blockreason': data['blockreason']
        }
    return response

@app.route('/api-blocked')
def apiblocked():
    return jsonify(blocked())

def getdefaultsettings(givejson=False):
    sett = {
        'suggestitems': 10,
        'openlinksinnewtab': False,
        'optinoverride': False,
        'atleastonelang': False
    }
    if givejson:
        return json.dumps(sett)
    else:
        return sett

def getsettings():
    tconn = tconnect()
    with tconn.cursor() as cur:
        sql = 'select settings from users where username=%s'
        cur.execute(sql, (getusername(), ))
        data = cur.fetchall()
    if len(data) == 0:
        with tconn.cursor() as cur:
            sql = 'insert into users(username, settings) values (%s, %s)'
            cur.execute(sql, (getusername(), getdefaultsettings(True)))
            tconn.commit()
        return getdefaultsettings()
    else:
        return json.loads(data[0][0])

@app.route('/api-settings', methods=['GET', 'POST'])
def settings():
    if logged():
        if request.method =='POST':
            tconn = tconnect()
            with tconn.cursor() as cur:
                sql = 'select id from users where username=%s'
                cur.execute(sql, (getusername(), ))
                data = cur.fetchall()
            if len(data) == 0:
                with tconn.cursor() as cur:
                    sql = 'insert into users(username, settings) values (%s, %s)'
                    cur.execute(sql, (getusername(), json.dumps(request.get_json())))
                    tconn.commit()
            else:
                with tconn.cursor() as cur:
                    sql = 'update users set settings=%s where username=%s'
                    cur.execute(sql, (json.dumps(request.get_json()), getusername()))
                    tconn.commit()
            response = {
                'status': 'ok',
                'settings': request.get_json(),
            }
            return jsonify(response)
        else:
            response = {
                'status': 'ok',
                'settings': getsettings()
            }
            return jsonify(response)
    else:
        response = {
            'status': 'error',
            'errorcode': 'mustlogin'
        }
        return make_response(response, 401)

@app.route('/login')
def login():
    """Initiate an OAuth login.
    Call the MediaWiki server to get request secrets and then redirect the
    user to the MediaWiki server to sign the request.
    """
    consumer_token = mwoauth.ConsumerToken(
        app.config['CONSUMER_KEY'], app.config['CONSUMER_SECRET'])
    try:
        redirect, request_token = mwoauth.initiate(
        app.config['OAUTH_MWURI'], consumer_token)
    except Exception:
        app.logger.exception('mwoauth.initiate failed')
        return flask.redirect(flask.url_for('index'))
    else:
        flask.session['request_token'] = dict(zip(
        request_token._fields, request_token))
        return flask.redirect(redirect)


@app.route('/oauth-callback')
def oauth_callback():
    """OAuth handshake callback."""
    if 'request_token' not in flask.session:
        flask.flash(u'OAuth callback failed. Are cookies disabled?')
        return flask.redirect(flask.url_for('index'))
    consumer_token = mwoauth.ConsumerToken(app.config['CONSUMER_KEY'], app.config['CONSUMER_SECRET'])

    try:
        access_token = mwoauth.complete(
        app.config['OAUTH_MWURI'],
        consumer_token,
        mwoauth.RequestToken(**flask.session['request_token']),
        flask.request.query_string)
        identity = mwoauth.identify(app.config['OAUTH_MWURI'], consumer_token, access_token)
    except Exception:
        app.logger.exception('OAuth authentication failed')
    else:
        flask.session['request_token_secret'] = dict(zip(access_token._fields, access_token))['secret']
        flask.session['request_token_key'] = dict(zip(access_token._fields, access_token))['key']
        flask.session['username'] = identity['username']
        tconn = tconnect()
        with tconn.cursor() as cur:
            sql = 'select settings from users where username=%s'
            cur.execute(sql, (getusername(), ))
            data = cur.fetchall()
        if len(data) == 0:
            with tconn.cursor() as cur:
                sql = 'insert into users(username, settings) values (%s, %s)'
                cur.execute(sql, (getusername(), getdefaultsettings(True)))
                tconn.commit()
    return flask.redirect(flask.url_for('index'))


@app.route('/logout')
def logout():
    """Log the user out by clearing their session."""
    flask.session.clear()
    return flask.redirect(flask.url_for('index'))

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
