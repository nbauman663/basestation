import unittest
import sqlite3
import xbeecom
import time
from db.db_init import init_db_app, db_resource
from flask import Flask
import os
import tempfile
import struct
import datetime
import sys
import logging


logging.basicConfig(format="[%(asctime)s " +
                    "%(filename)s:%(lineno)d %(levelname)s] %(message)s",
                    stream=sys.stdout,
                    level=logging.WARNING)


class MockSerial(object):

    def __init__(self, device, baud, timeout):
        self.device = device
        self.baud = baud
        self.timeout = timeout
        self.buffer = []
        self.wait_flag = False
        self.expect_data = []

    @classmethod
    def set_test_instance(cls, ut):
        cls.ut = ut

    def is_alive(self):
        return self.device

    def expect_write(self, data):
        self.expect_data.append(data)

    def write(self, data):
        self.ut.assertTrue(len(self.expect_data) > 0, "unexpected serial write")
        self.ut.assertEqual(data, self.expect_data.pop(0))

    def buffer_data(self, data):
        self.buffer += list(data)

    def buffer_wait(self):
        while self.inWaiting() > 0:
            time.sleep(0.01)
        self.wait_flag = True
        while self.wait_flag:
            time.sleep(0.01)

    def inWaiting(self):
        self.wait_flag = False
        return len(self.buffer)

    def read(self):
        self.ut.assertTrue(len(self.buffer) > 0, "read empty buffer")
        data = self.buffer.pop(0)
        return data

    def close(self):
        self.closed = True


def build_frame(contents):
    return ("\x7e\x00" + chr(len(contents)) + contents +
            chr(0xff & (0xff - sum(map(ord, contents)))))


def rx_indicator(address, rf_data):
    return build_frame("\x90" + address + "\xff\xfe\x00" + rf_data)


def build_sample(node, sm, st, at, vt):
    return rx_indicator(xbeecom.xbeecom.inverse_lookup[node],
                        struct.pack("!BHHHH", 1, sm, st, at, vt))


def tx_request(id, node, time):
    return build_frame("\x10" + chr(id) + xbeecom.xbeecom.inverse_lookup[node] +
                       "\xff\xfe\x00\x00\x02" + struct.pack("!H", time))


def tx_status(id, status):
    return build_frame("\x8b" + chr(id) + "\xff\xfe\x00" + status + "\x02")

rx_sample = build_frame("\x01\x08\x01\x07\x02\x06\x03")
modem_status = "\x7e\x00\x02\x8a\x00\x75"


class XbeeComTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class MockDt(datetime.datetime):
            pass

        xbeecom.datetime.datetime = MockDt
        xbeecom.serial.Serial = MockSerial

    def setUp(self):
        self.app = Flask(__name__)
        self.db, self.app.config["DATABASE"] = tempfile.mkstemp()
        init_db_app(self.app)

        MockSerial.set_test_instance(self)
        self.db_resource = db_resource(self.app)
        self.xbee = xbeecom.xbeecom(self.db_resource)
        self.xbee.__enter__()
        self.serial = self.xbee.ser

    def tearDown(self):
        self.xbee.__exit__(None, None, None)
        self.assertTrue(self.xbee.ser.closed, "serial port not closed")
        self.assertTrue(len(self.serial.expect_data) == 0, "data not received")

        xbeecom.datetime.datetime.now = datetime.datetime.now

        os.close(self.db)
        os.unlink(self.app.config["DATABASE"])

    def stub_now(self, *args):
        dt = datetime.datetime(*args)
        xbeecom.datetime.datetime.now = classmethod(lambda cls: dt)
        epoch = datetime.datetime(1970, 1, 1)
        return dt, (dt - epoch).total_seconds()

    def query(self, query_string):
        with self.db_resource as r:
            r.db.row_factory = sqlite3.Row
            result = r.db.execute(query_string).fetchall()
            return result

    def test_sample_time_up(self):
        dt = datetime.datetime(2016, 3, 2, 10, 5, 05)
        self.assertEqual(xbeecom.xbeecom.sample_time(dt),
                         datetime.datetime(2016, 3, 2, 10, 10, 0),
                         "incorrect datetime rounding")

    def test_sample_time_down(self):
        dt = datetime.datetime(2016, 3, 2, 10, 4, 05)
        self.assertEqual(xbeecom.xbeecom.sample_time(dt),
                         datetime.datetime(2016, 3, 2, 10, 00, 0),
                         "incorrect datetime rounding")

    def test_parse_sample(self):
        sample = {"rf_data": "\x01\x02\x03\x04\x05\x06\x07\x08\x09"}
        self.assertEqual(xbeecom.xbeecom.parse_sample(sample),
                         (1, 515, 1029, 1543, 2057))

    def test_parse_sample_no_voltage(self):
        sample = {"rf_data": "\x01\x02\x03\x04\x05\x06\x07"}
        self.assertEqual(xbeecom.xbeecom.parse_sample(sample),
                         (1, 515, 1029, 1543, 3300))

    def test_parse_sample_wrong_length(self):
        sample = {"rf_data": "\x01\x02\x03\x04\x05\x06\x07\x08"}
        with self.assertRaises(struct.error):
            xbeecom.xbeecom.parse_sample(sample)

    def test_moisture_conversion(self):
        samples = [
            [1.08, 0.020], [1.21, 0.048], [1.40, 0.129], [1.51, 0.183],
            [1.61, 0.210], [1.56, 0.237], [1.71, 0.223], [1.75, 0.273],
            [1.84, 0.309], [2.00, 0.332], [2.04, 0.333], [2.10, 0.394], ]
        samples = [(int((v * 9.1 / 31.1 + 0.05) * 4096), m) for v, m in samples]

        for sample, moisture in samples:
            result = xbeecom.xbeecom.convert_data((0, sample, 1, 1, 3300))
            self.assertEqual(result.raw_soil_moisture, sample, "wrong sample")
            self.assertLessEqual(abs(result.soil_moisture - moisture), 0.05,
                                 "moisture conversion accuracy worse than 5%")

    def test_temperature_conversion(self):
        samples = [
            [-40,  274], [-35,  301], [-30,  336], [-25,  383], [-20,  443],
            [-15,  520], [-10,  617], [-05,  739], [00,  889], [05, 1072],
            [10, 1292], [15, 1552], [20, 1857], [25, 2208], [30, 2605],
            [35, 3048], [40, 3533], [45, 4055], [35.5, 3100]]

        for temp, sample in samples:
            result = xbeecom.xbeecom.convert_data((0, 1, sample, 1, 3300))
            self.assertEqual(result.raw_soil_temp, sample, "wrong sample")
            self.assertLessEqual(abs(result.soil_temp - temp), 0.1,
                                 "|%0.2f - %0.2f| > 0.1" %
                                 (result.soil_temp, temp))

    def test_init(self):
        self.assertEqual(self.serial.is_alive(), "/dev/ttyUSB0",
                         "no serial port")

    @unittest.skip("removed feature")
    def test_tx_success(self):
        now, now_s = self.stub_now(2016, 3, 2, 19, 10, 00)
        self.serial.expect_write(tx_request(0, 1, 600))
        self.serial.buffer_data(build_sample(1, 1000, 2000, 3000, 3300))
        self.serial.buffer_wait()

        self.assertEqual(len(self.xbee.pending_tx), 1, "no pending response")
        self.assertEqual(self.xbee.tx_id, 1, "TX ID not incremented")

        self.serial.buffer_data(tx_status(0, "\x00"))
        self.serial.buffer_wait()

        self.assertEqual(len(self.xbee.pending_tx), 0, "status ignored")

    @unittest.skip("removed feature")
    def test_tx_success_weird_id(self):
        self.xbee.tx_id = 69
        now, now_s = self.stub_now(2016, 3, 2, 19, 10, 00)
        self.serial.expect_write(tx_request(69, 1, 600))
        self.serial.buffer_data(build_sample(1, 1000, 2000, 3000, 3300))
        self.serial.buffer_wait()

        self.assertEqual(len(self.xbee.pending_tx), 1, "no pending response")
        self.assertEqual(self.xbee.tx_id, 70, "TX ID not incremented")

        self.serial.buffer_data(tx_status(69, "\x00"))
        self.serial.buffer_wait()

        self.assertEqual(len(self.xbee.pending_tx), 0, "status ignored")

    @unittest.skip("removed feature")
    def test_tx_success_wrong_id(self):
        self.xbee.tx_id = 69
        now, now_s = self.stub_now(2016, 3, 2, 19, 10, 00)
        self.serial.expect_write(tx_request(69, 1, 600))
        self.serial.buffer_data(build_sample(1, 1000, 2000, 3000, 3000))
        self.serial.buffer_wait()

        self.assertEqual(len(self.xbee.pending_tx), 1, "no pending response")
        self.assertEqual(self.xbee.tx_id, 70, "TX ID not incremented")

        self.serial.buffer_data(tx_status(29, "\x00"))
        self.serial.buffer_wait()

        self.assertEqual(len(self.xbee.pending_tx), 1, "status not ignored")

    def test_tx_status(self):
        self.serial.buffer_data(tx_status(1, "\x00"))
        self.serial.buffer_wait()

    def test_tx_status_error(self):
        class ExpectWarning(logging.Filter):
            def __init__(self, ut_instance):
                self.warning_count = 1
                self.ut_instance = ut_instance

            def filter(self, record):
                if record.levelno != logging.WARNING:
                    return True
                self.warning_count -= 1
                if self.warning_count < 0:
                    self.ut_instance.assertTrue(False, "extra log message")
                return False

        f = ExpectWarning(self)
        xbeecom.logging.addFilter(f)
        try:
            self.serial.buffer_data(tx_status(1, "\x25"))
            self.serial.buffer_wait()
            self.assertEqual(f.warning_count, 0, "warning not received")
        finally:
            xbeecom.logging.removeFilter(f)

    def test_rx_sample(self):
        now, now_s = self.stub_now(2016, 3, 2, 19, 10, 00)
        self.serial.expect_write(tx_request(1, 1, 600))
        self.serial.buffer_data(build_sample(1, 1000, 2000, 3000, 3005))
        self.serial.buffer_wait()

        group = self.query("select * from sample_group")
        self.assertTrue(len(group) == 1, "missing sample_group insertion")
        self.assertEqual(group[0]["time"], now_s, "wrong sample_group time")
        result = self.query("select * from sample")
        self.assertTrue(len(result) == 1, "missing insertion")
        self.assertEqual(result[0]["s_id"], group[0]["id"], "wrong group")
        self.assertEqual(result[0]["time"], now.isoformat(), "mismatched dates")
        self.assertEqual(result[0]["raw_soil_moisture"], 1000, "wrong moisture")
        self.assertEqual(result[0]["raw_soil_temp"], 2000, "wrong soil temp")
        self.assertEqual(result[0]["raw_air_temp"], 3000, "mismatched air temp")
        self.assertEqual(result[0]["supply_voltage"], 3005, "wrong voltage")

    def test_multiple_rx_sample(self):
        now, now_s = self.stub_now(2016, 5, 2, 19, 10, 00)
        self.serial.expect_write(tx_request(1, 1, 600))
        self.serial.expect_write(tx_request(2, 2, 600))
        self.serial.buffer_data(build_sample(1, 10, 20, 30, 10))
        self.serial.buffer_data(build_sample(2, 3000, 50, 60, 10))
        self.serial.buffer_wait()

        group = self.query("select * from sample_group order by time")
        self.assertTrue(len(group) == 1, "wrong sample group insertions")
        result = self.query("select * from sample order by n_id")
        self.assertTrue(len(result) == 2, "wrong sample insertions")
        self.assertEqual(result[0]["raw_soil_temp"], 20, "wrong soil temp")
        self.assertEqual(result[1]["raw_soil_temp"], 50, "wrong soil temp")

    def test_multiple_rx_sample_group(self):
        now_1, now_s_1 = self.stub_now(2016, 1, 2, 19, 10, 00)
        self.serial.expect_write(tx_request(1, 1, 600))
        self.serial.buffer_data(build_sample(1, 1000, 300, 3000, 3200))
        self.serial.buffer_wait()
        now_2, now_s_2 = self.stub_now(2016, 1, 2, 19, 20, 00)
        self.serial.expect_write(tx_request(1, 1, 600))
        self.serial.buffer_data(build_sample(1, 1000, 200, 3000, 3100))
        self.serial.buffer_wait()

        group = self.query("select * from sample_group order by time")
        self.assertTrue(len(group) == 2, "missing sample_group insertion")
        self.assertEqual(group[0]["time"], now_s_1, "wrong sample_group time")
        self.assertEqual(group[1]["time"], now_s_2, "wrong sample_group time")
        result = self.query("select * from sample order by s_id, n_id")
        self.assertTrue(len(result) == 2, "missing insertion")
        self.assertEqual(result[0]["s_id"], group[0]["id"], "wrong group")
        self.assertEqual(result[1]["s_id"], group[1]["id"], "wrong group")
        self.assertEqual(result[0]["n_id"], 1, "wrong node")
        self.assertEqual(result[0]["time"], now_1.isoformat(), "wrong dates")
        self.assertEqual(result[1]["time"], now_2.isoformat(), "wrong dates")
        self.assertEqual(result[0]["raw_soil_temp"], 300, "wrong soil temp")
        self.assertEqual(result[1]["raw_soil_temp"], 200, "wrong soil temp")
        self.assertEqual(result[0]["supply_voltage"], 3200, "wrong voltage")
        self.assertEqual(result[1]["supply_voltage"], 3100, "wrong voltage")

    def test_duplicate_rx_sample(self):
        now, now_s = self.stub_now(2016, 3, 2, 19, 10, 00)
        self.serial.expect_write(tx_request(1, 1, 600))
        self.serial.expect_write(tx_request(1, 1, 600))
        self.serial.buffer_data(build_sample(1, 1000, 2000, 3000, 3300))
        self.serial.buffer_data(build_sample(1, 100, 200, 300, 3100))
        self.serial.buffer_wait()

        group = self.query("select * from sample_group")
        self.assertTrue(len(group) == 1, "missing sample_group insertion")
        self.assertEqual(group[0]["time"], now_s, "wrong sample_group time")
        result = self.query("select * from sample")
        self.assertTrue(len(result) == 1, "missing insertion")
        self.assertEqual(result[0]["s_id"], group[0]["id"], "wrong group")
        self.assertEqual(result[0]["time"], now.isoformat(), "mismatched dates")
        self.assertEqual(result[0]["raw_soil_moisture"], 1000, "wrong moisture")
        self.assertEqual(result[0]["raw_soil_temp"], 2000, "wrong soil temp")
        self.assertEqual(result[0]["raw_air_temp"], 3000, "mismatched air temp")
        self.assertEqual(result[0]["supply_voltage"], 3300, "wrong voltage")


if __name__ == "__main__":
    unittest.main()
