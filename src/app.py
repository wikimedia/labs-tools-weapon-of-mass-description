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
import yaml
import simplejson as json
import requests
from urllib.parse import quote
from flask import redirect, request, jsonify, make_response, render_template
import mwoauth
import mwparserfromhell
from requests_oauthlib import OAuth1
import random
import toolforge
import smtplib
from email.mime.text import MIMEText

app = flask.Flask(__name__)
application = app

ua = "Weapon of Mass Description (https://tools.wmflabs.org/weapon-of-mass-description; martin.urbanec@wikimedia.cz"
requests.utils.default_user_agent = lambda: ua

__dir__ = os.path.dirname(__file__)
app.config.update(yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))

key = app.config['CONSUMER_KEY']
secret = app.config['CONSUMER_SECRET']

def logged():
	return flask.session.get('username') != None

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
		return render_template('tool.html', logged=logged(),username=getusername())
	else:
		return render_template('login.html', loggeed=logged(), username=getusername())

@app.route('/api-item')
def apiitem():
	itemid = request.args.get('item')
	params = {
		"action": "wbgetentities",
		"format": "json",
		"ids": itemid,
		"redirects": "yes",
		"props": "sitelinks|labels|descriptions",
		"languages": "cs|en"
	}
	r = requests.get(app.config['API_MWURI'], params=params)
	data = r.json()['entities']
	response = {
		'status': 'ok'
	}
	items = []
	for entity in data:
		labels = []
		for label in data[entity]['labels']:
			labels.append(data[entity]['labels'][label])
		descriptions = []
		for description in data[entity]['descriptions']:
			descriptions.append(data[entity]['descriptions'][description])
		items.append({
			'labels': labels,
			'descriptions': descriptions,
			'qid': entity,
		})
	response['items'] = items
	return jsonify(response)

def langs():
	params = {
		"action": "sitematrix",
		"format": "json",
		"smtype": "language",
		"smstate": "all",
		"smlangprop": "code|name",
		"smlimit": "max"
	}
	r = requests.get(app.config['API_MWURI'], params=params)
	data = r.json()
	langs = []
	for key in data['sitematrix'].keys():
		if key != 'count':
			langs.append({
				'code': data['sitematrix'][key]['code'],
				'name': data['sitematrix'][key]['name']
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
	if username == None:
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

	return flask.redirect(flask.url_for('index'))


@app.route('/logout')
def logout():
	"""Log the user out by clearing their session."""
	flask.session.clear()
	return flask.redirect(flask.url_for('index'))

if __name__ == "__main__":
	app.run(debug=True, threaded=True)
