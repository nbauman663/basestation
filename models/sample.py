from collections import namedtuple as nt
import logging
import datetime

id_str_lookup = {
    "soil_temp1": "@ 25 cm ",
    "soil_temp2": "@ 10 cm ",
    "soil_temp3": " @ 5 cm",
    "soil_moisture1": "@ 25 cm ",
    "soil_moisture2": "@ 10 cm ",
    "soil_moisture3": "@ 5 cm ",
    "soil_EC1": "@ 25 cm ",
    "soil_EC2": "@ 10 cm ",
    "soil_DP1": "@ 25 cm ",
    "soil_DP2": "@ 10 cm ",
    "uva": "UVA ",
    "uvb": "UVB ",
}

class Samples(object):
    _fields = ("id", "n_id", "s_id", "time",
               "air_temp", "air_rh", "uva", "uvb", "uvi", "soil_temp1",
               "soil_moisture1", "soil_EC1", "soil_DP1", "soil_temp2",
               "soil_moisture2", "soil_EC2", "soil_DP2", "soil_temp3",
               "soil_moisture3", "wind_speed", "wind_direction")
    # True false indicates whether it is checked or not initially in download page
    descriptions = (
        ("n_id", "Node number.", True),
        ("time", "ISO formatted sample timestamp.", True),
        ("air_temp", "Air temperature in degrees Celsius.", True),
        ("air_rh", "Air relative humidity in percent", False),
        ("uva", "UVA solar irradiance in kW/m^2", False),
        ("uvb", "UVB solar irradiance in kW/m^2", False),
        ("uvi", "UV Index", False),
        ("soil_temp1", "Soil temperature at 25 cm underground in degrees Celsius.", True),
        ("soil_moisture1", "Soil moisture at 25 cm underground in percent VWC.", True),
        ("soil_EC1", "Soil electroconductivity at 25 cm underground in dS/m.", False),
        ("soil_DP1", "Soil apparent dielectric permittivity at 10 cm underground.", False),
        ("soil_temp2", "Soil temperature at 10 cm underground in degrees Celsius.", False),
        ("soil_moisture2", "Soil moisture at 10 cm underground in percent VWC.", False),
        ("soil_EC2", "Soil electroconductivity at 10 cm underground in dS/m.", False),
        ("soil_DP2", "Soil apparent dielectric permittivity at 10 cm underground.", False),
        ("soil_temp3", "Soil temperature at 5 cm underground.", False),
        ("soil_moisture3", "Soil moisture at 5 cm underground in percent VWC.", False),
        ("wind_speed", "Wind speed in m/s.", False),
        ("wind_direction", "Wind direction in degrees bearing where north is 0 deg", False),
        ("id", "Unique identifier for each sample.", False),
        ("s_id", "Unique identifier for each ten minute sample group.", False)
    )

    def __init__(self, fields, rows):
        self.fields = fields
        self.rows = rows

    @classmethod
    def fields(cls, fields=None, average=None, max_min=False, time_prefix=None, exact_time=True):
        fields = cls._fields if fields is None else fields

        if average is not None:
            if exact_time:
                if "daily" in average:
                    result = "s.n_id, strftime('%Y-%m-%d', s.time) AS sample_time, "
                elif "monthly" in average:
                    result = "s.n_id, strftime('%Y-%m', s.time) AS sample_time, "
                elif "yearly" in average:
                    result = "s.n_id, strftime('%Y', s.time) AS sample_time, "
                else:
                    logging.error("Average string is not valid")
            else:
                if "daily" in average:
                    result = "s.n_id, CAST((strftime('%s', datetime(s.time, 'start of day'))) AS int) AS sample_time, "
                elif "monthly" in average:
                    result = "s.n_id, CAST((strftime('%s', datetime(s.time, 'start of month'))) AS int) AS sample_time, "
                elif "yearly" in average:
                    result = "s.n_id, CAST((strftime('%s', datetime(s.time, 'start of year'))) AS int) AS sample_time, "
                else:
                    logging.error("Average string is not valid")

            if max_min:
                result += ", ".join(("AVG(s." + f + ") AS " + f + ", "
                                     "MIN(s." + f + ") AS " + f + "_min, " +
                                     "MAX(s." + f + ") AS " + f + "_max" for f in fields))
            else:
                result += ", ".join(("AVG(s." + f + ") AS " + f for f in fields))

            return result
        else:
            if time_prefix is not None:
                fields = list(fields)
                fields.remove("time")

            result = ", ".join(("s." + f for f in fields))

            if time_prefix is not None:
                result += ", " + time_prefix + ".time"
            result += " AS sample_time"
        return result

    @classmethod
    def get_status(cls, db):
        query = """
        select {0}
        from sample s
        inner join (
            select sg2.id, max(sg2.time)
            from sample_group sg2) sg on sg.id = s.s_id
        """.format(cls.fields())
        results = cls(cls._fields, db.execute(query).fetchall())
        return results.to_struct()

    @classmethod
    def get_samples(cls, db, start_date=None, end_date=None, nodes=range(1, 8),
                    fields=None, average=None, max_min=False, exact_time=True):

        # could clean this up but why fix what isn't broken . . .
        start_utc_offset = (datetime.datetime.fromtimestamp(start_date) - datetime.datetime.utcfromtimestamp(start_date)).seconds
        end_utc_offset = (datetime.datetime.fromtimestamp(end_date) - datetime.datetime.utcfromtimestamp(end_date)).seconds
        if average is not None:
            if "monthly" in average:
                raw_start_date = datetime.datetime.fromtimestamp(start_date)
                start_date = (datetime.date(raw_start_date.year, raw_start_date.month, 1)).strftime('%s')
                start_date = int(start_date) + start_utc_offset - 86400   # 86400 = 1 day

                raw_end_date = datetime.datetime.fromtimestamp(end_date)
                if raw_end_date.month == 12:
                    end_date_month = 1
                    end_date_year = raw_end_date.year + 1
                else:
                    end_date_month = raw_end_date.month + 1
                    end_date_year = raw_end_date.year
                end_date = (datetime.date(end_date_year, end_date_month, 1)).strftime('%s')
                end_date = int(end_date) + end_utc_offset - 86400       # 86400 = 1 day
            elif "yearly" in average:
                raw_start_date = datetime.datetime.fromtimestamp(start_date)
                start_date = (datetime.date(raw_start_date.year, 1, 1)).strftime('%s')
                start_date = int(start_date) + 64800 - 86400  # utc offset - one day

                raw_end_date = datetime.datetime.fromtimestamp(end_date)
                end_date = (datetime.date(raw_end_date.year+1, 1, 1)).strftime('%s')
                end_date = int(end_date) + 64800 - 86400    # utc offset - one day
        else:
            start_date = start_date + start_utc_offset - 86400      # 86400 = 1 day
            end_date = end_date + end_utc_offset

        fields = cls._fields if fields is None else tuple(fields)
        time_prefix = None if exact_time else "sg"
        query = """
        select {0}
        from sample s
        inner join (
            select sg2.id, sg2.time
            from sample_group sg2
            where sg2.time > {1} and sg2.time < {2}
            ) sg on sg.id = s.s_id
        where s.n_id in ({3})
        {4}
        """.format(cls.fields(fields=fields,
                              average=average,
                              max_min=max_min,
                              time_prefix=time_prefix,
                              exact_time=exact_time),
                   start_date,
                   end_date,
                   ",".join(map(str, nodes)),
                   "order by s.n_id, sg.id" if average is None else "group by s.n_id, sample_time")

        # logging.info("query: {0}".format(query))
        results = cls(fields, db.execute(query).fetchall())

        override_fields = []
        if average is not None:
            override_fields.append("n_id")
            override_fields.append("time")
            for f in fields:
                override_fields.append(f + "_avg")
                if max_min:
                    override_fields.append((f + "_min"))
                    override_fields.append((f + "_max"))

        return results.to_struct(override_fields)

    @classmethod
    def get_bg_samples(cls, db, fields):
        fields = cls._fields if fields is None else tuple(fields)
        fields_str = ", ".join((f for f in fields))
        not_null_str = " AND ".join((f + " IS NOT NULL" for f in fields))
        results = []
        nodes = [1, 2, 3, 4, 5, 6, 7]
        if (fields[0] == "wind_direction") or (fields[0] == "wind_speed"):
            nodes = [1, 4,  7]

        for i in nodes:
            query = """
            select {0}
            from sample s
            where n_id in ({1}) AND {2}
            ORDER BY id DESC LIMIT 1
            """.format(fields_str,
                       i,
                       not_null_str)

            # logging.info("Query:" + query)

            results += db.execute(query).fetchall()

        # logging.info("Results: {0}".format(results))

        field_offset = 0
        formatted_results = dict()
        for f in fields:
            res_arr = []
            for r in results:
                res_arr.append(r[field_offset])
            formatted_results[id_str_lookup[f] if len(list(fields))>1 else ""] = res_arr
            field_offset += 1

        return formatted_results

    def to_struct(self, override_fields=[]):
        # logging.info("self.fields: {0}".format(self.fields))
        # logging.info("override_fields: {0}".format(override_fields))
        if not override_fields:
            sample = nt("sample", self.fields)
            return {"fields": self.fields,
                    "results": [sample(*row) for row in self.rows]}
        else:
            sample = nt("sample", override_fields)
            return {"fields": override_fields,
                    "results": [sample(*row) for row in self.rows]}










