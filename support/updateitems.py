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

with open('/data/scratch/weapon-of-mass-description-items.sql', 'w', 1) as f:
	f.write('use s53612__weapon_of_mass_description_p;\n')
	f.write('drop table if exists items;\n')
	f.write('create table items (qid varchar(255));\n')
	wdconn = wdconnect()
	with wdconn.cursor() as cur:
		sql = 'select page_title from page where page_namespace=0 and page_is_redirect=0 order by page_id'
		cur.execute(sql)
		for row in ResultIter(cur):
			sql = 'insert into items(qid) values("%s");\n' % (row[0], )
			f.write(sql)
