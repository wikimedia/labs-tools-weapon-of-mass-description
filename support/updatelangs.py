#!/usr/bin/env python

from __future__ import generators
import toolforge
import pymysql
import os

# Get languages from wikidatawiki_p
wdconn = toolforge.connect('wikidatawiki', cluster='analytics')
with wdconn.cursor() as cur:
	sql = 'select distinct term_language from wb_terms where term_type="label"'
	cur.execute(sql)
	data = cur.fetchall()

with open('/data/scratch/weapon-of-mass-description-update-langs.sql', 'w') as f:
	f.write('use s53612__weapon_of_mass_description_p;\n')
	f.write('drop table if exists langs;\n')
	f.write('create table langs (language varchar(20));\n')
	for row in data:
		sql = 'insert into langs(language) values("%s")\n' % (row[0], )
		f.write(sql)

os.system('cat /data/scratch/weapon-of-mass-description-update-langs.sql | sql local')
os.remove('/data/scratch/weapon-of-mass-description-update-langs.sql')
