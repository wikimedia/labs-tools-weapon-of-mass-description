#!/usr/bin/env python

from __future__ import generators
import toolforge
import pymysql
import os

def ResultIter(cursor, arraysize=100):
	'An iterator that uses fetchmany to keep memory usage down'
	while True:
		results = cursor.fetchmany(arraysize)
		if not results:
			break
		for result in results:
			yield result

def wdconnect():
	return toolforge.connect('wikidatawiki', cluster='analytics')

def tconnect():
	return pymysql.connect(
		database='s53612__weapon_of_mass_description_p',
		host='tools.db.svc.eqiad.wmflabs',
		read_default_file=os.path.expanduser("~/replica.my.cnf"),
		charset='utf8mb4',
	)

TERM_TYPES = ['label', 'description']

# Get all languages from database
tconn = tconnect()
with tconn.cursor() as cur:
	sql = 'select language from langs'
	cur.execute(sql)
	data = cur.fetchall()
	langs = []
	for row in data:
		langs.append(row[0])

with tconn.cursor() as cur:
	sql = 'drop table if exists yes'
	cur.execute(sql)
with tconn.cursor() as cur:
	sql = 'create table yes (qid varchar(255), lang varchar(20), type varchar(20));'
	cur.execute(sql)

for term_type in TERM_TYPES:
	for lang in langs:
		wdconn = wdconnect()
		with wdconn.cursor() as wdcur:
			sql = 'select term_entity_id from wb_terms where term_type="%s" and term_language="%s";' % (term_type, lang)
			wdcur.execute(sql)
			tconn = tconnect()
			for row in ResultIter(wdcur):
				with tconn.cursor() as tcur:
					sql = 'insert into yes(qid, lang, type) values ("Q%s", "%s", "%s")' % (row[0], lang, term_type)
					tcur.execute(sql)
		break # debug
