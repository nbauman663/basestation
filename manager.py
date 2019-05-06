# manager for the database, few commands
import db.db_init as db_init
import sys
import random
import time
import datetime
import math
import sqlite3
import xbeecom


def iso_to_timestamp(iso):
    dt = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.%f")
    r_dt = xbeecom.xbeecom.sample_time(dt)
    return int((r_dt - datetime.datetime(1970, 1, 1)).total_seconds())


if __name__ == "__main__":
    if sys.argv[1] == 'db_init':
        print 'Initializing Database! :D xD'
        db_init.init_db()
    elif sys.argv[1] == 'fake_data':
        print 'Copy pasting our degree'
        now = int(time.time())
        start = now - 60*60*24*365
        print now, start
        db = db_init.connect_stand_alone()

        db.executemany("""insert into sample_group(time)
                       values (?)""", [[i] for i in range(start, now, 60*10)])

        values = []
        for t in xrange(start, now, 60*10):
            for n_id in range(1, 8):
                year = (t % (60 * 60 * 24 * 365))/(60 * 60 * 24 * 365)
                values.append((
                    n_id,
                    t,
                    datetime.datetime.fromtimestamp(t).isoformat(),
                    10.0 - 20.0 * math.cos(2 * math.pi * year) * random.normalvariate(0, 0.5),
                    10.0 - 10.0 * math.cos(2 * math.pi * year) * random.normalvariate(0, 0.5),
                    20.0 - 20.0 * math.cos(2 * math.pi * year) * random.normalvariate(0, 0.5),
                    2000,
                    1000,
                    3000
                ))
        print '{0} samples generated'.format(len(values))
        db.executemany('''insert into sample (
                        n_id, s_id, time,
                        air_temp, soil_temp, soil_moisture,
                        raw_air_temp, raw_soil_temp, raw_soil_moisture)
                       values (?,
            (select sg.id from sample_group sg where sg.time=?),
            ?, ?, ?, ?, ?, ?, ?)''',
                       values)

        db.commit()
        print db.execute('select count(*) from sample').fetchall()
        print 'samples inserted into database'
    elif sys.argv[1] == "transfer_db":
        db = sqlite3.connect("Tritz.db")
        data = db.execute("""select
                   n_id, time, soil_moisture, soil_temp, air_temp
                   from sample
                   where id > 368225""").fetchall()
        db.close()

        db = db_init.connect_stand_alone()
        # convert_data() has been deleted !
        values = [[row[0], iso_to_timestamp(row[1]), row[1]] +
                  list(xbeecom.xbeecom.convert_data([1] + list(row[2:])))
                  for row in data]
        db.executemany("insert or ignore into sample_group (time) values(?)",
                       map(lambda row: (row[1],), values))
        db.executemany("""
                     insert or ignore into sample (
                        n_id, s_id, time,
                        soil_moisture, soil_temp, air_temp,
                        raw_soil_moisture, raw_soil_temp, raw_air_temp)
                     values (?, (
                        select sg.id
                        from sample_group sg
                        where sg.time = ?),
                     ?, ?, ?, ?, ?, ?, ?);
                     """, values)
        db.commit()
        db.close()
    elif sys.argv[1] == "supply_voltage":
        db = db_init.connect_stand_alone()
        db.execute("""alter table sample
                   add column supply_voltage integer;""")

        db.execute("""
                   update sample
                   set supply_voltage = 3300 where supply_voltage ISNULL;
                   """)
        db.commit()
        db.close()
    else:
        print 'Unknown Command'
