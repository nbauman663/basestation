
-- deletes table if exists already
drop table if exists node;
drop table if exists sample;
drop table if exists sample_group;
/* Nate: node table does not appear to actually be used !!!*/
create table node(
	id integer primary key autoincrement,
	name text not null,
	lat integer not null,
	lon integer not null,
	elv integer not null
);

create table sample_group(
	id integer primary key autoincrement,
	time integer not null,
	unique(time)
);

create table sample(
	id integer primary key autoincrement,
	n_id integer not null,
	s_id integer not null,
	time text not null,
	air_temp real,
	air_rh real,
	uva real,
	uvb real,
	uvi real,
	soil_temp1 real,
	soil_moisture1 real,
	soil_EC1 real,
	soil_DP1 real,
	soil_temp2 real,
	soil_moisture2 real,
	soil_EC2 real,
	soil_DP2 real,
	soil_temp3 real,
	soil_moisture3 real,
	wind_speed real,
	wind_direction integer
);

/* Nate: not 100% sure about what these indecies do . . . */
create index node_index on sample(n_id);
create index time_index on sample_group(time);
create index sample_index on sample(s_id);

