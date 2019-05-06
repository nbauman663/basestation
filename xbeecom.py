import serial
import struct
from xbee import ZigBee
import datetime
import time
import sys
import traceback
import collections
import logging
import math
from teros12_converter import calculate_vwc
from teros12_converter import calculate_dp


logging = logging.getLogger(__name__)


class xbeecom(object):
    node_lookup = {
        "\x00\x13\xA2\x00\x40\xDC\x45\x28": 1,
        "\x00\x13\xA2\x00\x41\x4e\x03\xb5": 2,
        "\x00\x13\xa2\x00\x41\x4e\x03\x74": 3,
        "\x00\x13\xA2\x00\x41\x91\x1A\x49": 4,
        "\x00\x13\xa2\x00\x41\x4e\x03\xbd": 5,
        "\x00\x13\xa2\x00\x40\xd8\x3b\x40": 6,
        "\x00\x13\xa2\x00\x41\x4e\x03\x7c": 7,
    }
    inverse_lookup = {v: k for k, v in node_lookup.items()}

    # object constructor, get_db is function to return the db object
    def __init__(self, get_db):
        self.get_db = get_db

    # implicitly called by 'with' statement, aquires serial port resources
    def __enter__(self):
        while True:
            try:
                self.ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
                break
            except serial.serialutil.SerialException:
                logging.error("could not establish serial connection")
                time.sleep(5)
        self.xbee = ZigBee(self.ser, callback=self.build_callback())
        return self

    # called when 'with' statement terminates, releases serial port resources
    def __exit__(self, exc_type, exc_value, traceback):
        self.xbee.halt()
        self.ser.close()

    # factory function to create xbeecom callback function
    # function that makes a function, for the purpose of constructing
    def build_callback(self):
        def handle_frame(data):
            try:
                # logging.debug("handling frame: %s", str(data))
                if data["id"] == "tx_status":
                    if data["deliver_status"] != "\x00":
                        logging.warning("failed transmission for node %d",
                                        ord(data["frame_id"]))
                elif data["id"] == "rx":
                    with self.get_db as r:
                        self.write_sample(data, r)
                else:
                    logging.warning("unknown frame type")
            except Exception as e:
                logging.exception("unhandled %s" % type(e).__name__)
        return handle_frame

    # this method has been altered -NATE
    @classmethod
    def parse_sample(self, data):
        data = data["rf_data"]
        # logging.info("rf_data: %s", data)
        split_data = data.split()
        if len(split_data) == 15:
            return split_data
        else:
            logging.error("incorrect packet size");

    @classmethod
    def convert_data(cls, parse_data, cur_node):
        sample_data = dict()

        air_temp = float(parse_data[1])
        air_rh = float(parse_data[2])
        if air_temp == -999:
            logging.error("Node {0}: Temperature and RH sensor failed!".format(cur_node))
        else:
            sample_data["air_temp"] = air_temp
            if air_rh > 100:
                sample_data["air_rh"] = 100
            else:
                sample_data["air_rh"] = air_rh

        uva = float(parse_data[3])/100
        uvb = float(parse_data[4])/100
        uvi = float(parse_data[5])

        # uva/uvb scaled using Campbell Scientific UV sensor
        # uvi scaled using NOAA solar noon UV predictions
        if (uvi < -1) or (uvi > 14):
            logging.error("Node {0}: UV sensor failed!".format(cur_node))
        else:
            if uvi < 0:
                sample_data["uvi"] = 0
                sample_data["uva"] = 0
                sample_data["uvb"] = 0
            elif cur_node == 1:
                sample_data["uva"] = uva * 1.04
                sample_data["uvb"] = uvb * 1.04
                sample_data["uvi"] = int(round(uvi * 1.14))
            elif cur_node == 2:
                sample_data["uva"] = uva * 1.07
                sample_data["uvb"] = uvb * 1.07
                sample_data["uvi"] = int(round(uvi * 1.19))
            elif cur_node == 3:
                sample_data["uva"] = uva * 1.34
                sample_data["uvb"] = uvb * 1.34
                sample_data["uvi"] = int(round(uvi * 1.47))
            elif cur_node == 4:
                sample_data["uva"] = uva * 0.86
                sample_data["uvb"] = uvb * 0.86
                sample_data["uvi"] = int(round(uvi))
            elif cur_node == 5:
                sample_data["uva"] = uva * 1.46
                sample_data["uvb"] = uvb * 1.46
                sample_data["uvi"] = int(round(uvi * 1.65))
            elif cur_node == 6:
                sample_data["uva"] = uva * 1.46
                sample_data["uvb"] = uvb * 1.46
                sample_data["uvi"] = int(round(uvi * 1.83))
            elif cur_node == 7:
                sample_data["uva"] = uva * 1.39
                sample_data["uvb"] = uvb * 1.39
                sample_data["uvi"] = int(round(uvi * 1.75))


        soil_temp1 = float(parse_data[6])
        if soil_temp1 == -999:
            logging.error("Node {0}: TEROS 12 1 failed!".format(cur_node))
        else:
            sample_data["soil_temp1"] = soil_temp1
            sample_data["soil_moisture1"] = calculate_vwc(float(parse_data[7]))
            sample_data["soil_EC1"] = float(parse_data[8])/1000
            sample_data["soil_DP1"] = calculate_dp(float(parse_data[7]))

        soil_temp2 = float(parse_data[9])
        if soil_temp2 == -999:
            logging.error("Node {0}: TEROS 12 2 failed!".format(cur_node))
        else:
            sample_data["soil_temp2"] = soil_temp2
            sample_data["soil_moisture2"] = calculate_vwc(float(parse_data[10]))
            sample_data["soil_EC2"] = float(parse_data[11])/1000
            sample_data["soil_DP2"] = calculate_dp(float(parse_data[10]))

        soil_moisture3 = float(parse_data[12])
        if soil_moisture3 < 0:
            logging.error("Node {0}: ADC failed!".format(cur_node))
        else:
            sample_data["soil_moisture3"] = soil_moisture3

        if cur_node == 1 or cur_node == 4 or cur_node ==7:
            wind_speed = float(parse_data[13])
            wind_direction = float(parse_data[14])
            if wind_speed > 0:
                sample_data["wind_speed"] = wind_speed
                if wind_direction >= 0 and wind_direction <= 360:
                    if cur_node == 1:
                        wind_direction = (wind_direction - 15)
                    sample_data["wind_direction"] = wind_direction % 360
            else:
                sample_data["wind_speed"] = 0
                sample_data["wind_direction"] = -1


        return sample_data

    def write_sample(self, data, r):
        parse_data = self.parse_sample(data)
        address = data['source_addr_long']
        try:
            cur_node = self.node_lookup[address]
            # logging.debug("received sample from node %d", cur_node)
        except KeyError:
            logging.error("unknown sender address: 0x%s", address.encode("hex"))
            cur_node = 0

        now = datetime.datetime.now()
        sample_time = self.sample_time(now)

        epoch = datetime.datetime(1970, 1, 1)
        sample_seconds = (sample_time - epoch).total_seconds()
        sample_data = self.convert_data(parse_data,cur_node)
        # logging.info("saving sample for node %d, %s", cur_node, sample_data)

        # args = ([cur_node, sample_seconds, now.isoformat()] + list(sample_data))

        cur = r.db.cursor()
        cur.execute("insert or ignore into sample_group (time) values (?);",
                    (sample_seconds,))

        query = """
         insert or ignore into sample (
            n_id, s_id, time, {0})
         values ({1}, (
            select sg.id
            from sample_group sg
            where sg.time = {2}),
         ?, {3});
         """.format(", ".join((str(f) for f in sample_data.keys())),
                    cur_node, sample_seconds,
                    ", ".join((str(f) for f in sample_data.values())))

        # logging.info("query: {0}".format(query))

        cur.execute(query, ([now.isoformat()]))

        r.db.commit()
        # logging.debug("data written to database")
        # logging.debug("sample seconds: %s", sample_seconds)

    # this rounds the time packets are received so they can be grouped.
    @classmethod
    def sample_time(self, dt):
        roundTo = 600
        seconds = (dt - dt.min).seconds
        # // is a floor division, not a comment on following line:
        rounding = (seconds+roundTo/2) // roundTo * roundTo
        return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)
