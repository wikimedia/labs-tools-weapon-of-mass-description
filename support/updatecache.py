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

tconn = tconnect()
with tconn.cursor() as cur:
	#sql = 'select distinct term_language from wb_terms where term_type="label"'
	sql = 'select language from langs'
	cur.execute(sql)
	data = cur.fetchall()
	langs = []
	for row in data:
		langs.append(row[0])

for term_type in TERM_TYPES:
	table = 'no_%s' % (term_type, )
	tconn = tconnect()
	with tconn.cursor() as cur:
		sql = 'drop table if exists %s_new' % (table, )
		cur.execute(sql)
	with tconn.cursor() as cur:
		sql = '''create table %s_new
		(
			qid varchar(256),
			language varchar(256)
		)
		''' % (table, )
		cur.execute(sql)
	for lang in langs:
		wdconn = wdconnect()
		with wdconn.cursor() as cur:
			sql = 'select page_title from page where cast(replace(page_title, "Q", "") as int) not in (select term_entity_id from wb_terms where term_type="%s" and term_language="%s") and page_namespace=0 and page_is_redirect=0' % (term_type, lang)
			print(sql)
			cur.execute(sql)
			tconn = tconnect()
			for row in ResultIter(cur):
				with tconn.cursor() as cur2:
					sql = 'insert into %s_new(qid, language) values ("%s", "%s")' % (table, row[0], lang)
					cur2.execute(sql)
		break # debug
	tconn = tconnect()
	with tconn.cursor() as cur:
		sql = 'drop table if exists %s_old' % (table, )
		cur.execute(sql)
	with tconn.cursor() as cur:
		sql = 'alter table %s rename to %s_old' % (table, table)
		cur.execute(sql)
	with tconn.cursor() as cur:
		sql = 'alter table %s_new rename to %s' % (table, table)
		cur.execute(sql)
