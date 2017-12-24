#!/usr/bin/env python

from __future__ import generators
import toolforge
import pymysql
import os

def ResultIter(cursor, arraysize=1000):
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

wdconn = wdconnect()
tconn = tconnect()
with tconn.cursor() as cur:
	sql = 'drop table if exists items'
	cur.execute(sql)
with tconn.cursor() as cur:
	sql = '''create table items
	(
		full_entity_id varchar(255),
		entity_id int
	)'''
	cur.execute(sql)

limit = 1000
offset = 0
cont = True
while cont:
	wdconn = wdconnect()
	tconn = tconnect()
	with wdconn.cursor() as wdcur:
		sql = 'select page_title from page where page_namespace=0 and page_is_redirect=0 limit %s offset %s' % (limit, offset)
		wdcur.execute(sql)
		if wdcur.rowcount < limit:
			cont = False
		else:
			offset += limit
		for row in ResultIter(wdcur):
			with tconn.cursor() as tcur:
				sql = 'insert into items(full_entity_id, entity_id) values ("%s", %s)' % (row[0], int(row[0].replace('Q', '')))
				tcur.execute(sql)
