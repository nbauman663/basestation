# main file for whole database program
# it's a controller for whole thing - royce wilson

# imports!
from datetime import datetime
import time
from flask import Flask, request, session, g, redirect, url_for, \
    abort, render_template, flash, jsonify, Response, send_from_directory
from werkzeug.routing import BaseConverter
from db.db_init import connect_db, db_resource
from xbeecom import xbeecom
from models.sample import Samples
import sys
import os
import itertools
import operator
import logging


logging.basicConfig(format="[%(asctime)s %(name)s %(levelname)s] %(message)s",
                    filename="log.log",
                    level=logging.DEBUG)

# creation!
app = Flask(__name__)
app.config.from_object('db.dbconfig')
app.logger.disabled = True
log = logging.getLogger('werkzeug')
log.disabled = True

id_str_lookup = {
    "soil_temp1": " @ 25 cm",
    "soil_temp2": " @ 10 cm",
    "soil_temp3": " @ 5 cm",
    "soil_moisture1": " @ 25 cm",
    "soil_moisture2": " @ 10 cm",
    "soil_moisture3": " @ 5 cm",
    "soil_EC1": " @ 25 cm",
    "soil_EC2": " @ 10 cm",
    "soil_DP1": " @ 25 cm",
    "soil_DP2": " @ 10 cm",
    "uva": " UVA",
    "uvb": " UVB",
}

class ListConverter(BaseConverter):
    def to_python(self, value):
        return value.split("+")

    def to_url(self, values):
        return "+".join(map(BaseConverter.to_url, values))
app.url_map.converters["list"] = ListConverter


iso_format_string = "%Y-%m-%dT%H:%M:%S"
@app.context_processor
def utility_processor():
    def format_date(time):
        return datetime.utcfromtimestamp(time).strftime("%Y-%m-%d %H:%M:%S")
    return dict(format_date=format_date)


@app.before_request
def before_request():
    g.db = connect_db(app)


@app.teardown_request
def teardown_request(excetion):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/')
def graph():
    recent_samples = Samples.get_status(g.db)
    recent_samples = [dict(zip(recent_samples["fields"], sample))
                      for sample in recent_samples["results"]]
    return render_template('graph2.html', nodes=range(1,8))


@app.route('/instantaneous')
def instantaneous():
    return render_template('instantaneous.html')


@app.route('/download', methods=['GET', 'POST'])
def download():
    if request.method == 'POST':
        try:
            nodes = [int(n.partition('-')[-1])
                     for n in request.form.keys()
                     if n.startswith('node-')]
            nodes = set(nodes) & set(range(1, 8))
        except ValueError:
            pass

        # strip field- off of post parameters
        fields = [f.partition('-')[-1]
                  for f in request.form.keys()
                  if f.startswith('field-')]
        # only include actual field names
        fields = set(fields) & set(Samples._fields)

        start_date = int(time.mktime(datetime.strptime(request.form['start'], '%m/%d/%Y').timetuple()))
        end_date = int(time.mktime(datetime.strptime(request.form['end'], '%m/%d/%Y').timetuple()))
        end_date += 60*60*24

        average = request.form['average']
        if "none" in average:
            average = None
        else:
            # bypassing potential runtime exceptions
            try:
                fields.remove("time")
            except:
                pass

            try:
                fields.remove("n_id")
            except:
                pass

        result = Samples.get_samples(g.db, start_date, end_date, nodes,
                                [f for f in Samples._fields if f in fields], average, True)
        csv = ','.join(result['fields']) + '\n'
        csv += '\n'.join(','.join(map(str, row)) for row in result['results'])
        return Response(
            csv,
            mimetype="text/csv",
            headers={"Content-disposition":
                     "attachment; filename=data.csv"})
    else:
        return render_template('download.html', nodes=range(1,8), fields=Samples.descriptions)

@app.route('/data/status')
def node_status():
    return jsonify(Samples.get_status(g.db))

# need new field here
@app.route("/data")
def get_samples():
    try:
        start_date = request.args.get("start")
        if start_date is not None:
            start_date = int(start_date) / 1000

        end_date = request.args.get("end")
        if end_date is not None:
            end_date = int(end_date) / 1000

        nodes = request.args.get("nodes")
        if nodes is not None:
            nodes = tuple(set(map(int, (n for n in nodes.split("+")))))

        y_axis = request.args.get("field_y")
        if y_axis is not None:
            y_axis = list(map(str, (y for y in y_axis.split("+"))))
            if y_axis[0] in "on":
                y_axis.remove("on")

        # x_axis = request.args.get("field_x")

        average = request.args.get("average")

        if "none" in average:
            average = None
            fields = []
            fields.extend(y_axis)
            fields.append("n_id")
            fields.append("time")
        else:
            fields = set(y_axis) & set(Samples._fields)

        max_min = (request.args.get("max_min") == "true")

    except ValueError as e:
        return jsonify({"error": "Error parsing fields: {0}".format(e)})

    samples = Samples.get_samples(g.db, start_date, end_date,
                                  nodes, fields, average, max_min, exact_time=False)

    node_id_offset = samples["fields"].index("n_id")
    sample_time_offset = samples["fields"].index("time")

    series = dict()
    for y in y_axis:
        # logging.info("y axis: {0}".format(y))
        if len(y_axis) > 1:
            id_str = id_str_lookup[y]
        else:
            id_str = ""

        if max_min:
            y_axis_offset = samples["fields"].index(y + "_avg")
            groups = itertools.groupby(samples["results"], operator.itemgetter(node_id_offset))
            for k, group in groups:
                new_dict = {("Node " + str(k) + id_str + " avg"): [(s[sample_time_offset] * 1000, s[y_axis_offset])for s in group]}
                series.update(new_dict)

            groups = itertools.groupby(samples["results"], operator.itemgetter(node_id_offset))
            for k, group in groups:
                new_dict = {("Node " + str(k) + id_str + " min"): [(s[sample_time_offset] * 1000, s[y_axis_offset + 1])for s in group]}
                series.update(new_dict)

            groups = itertools.groupby(samples["results"], operator.itemgetter(node_id_offset))
            for k, group in groups:
                new_dict = {("Node " + str(k) + id_str + " max"): [(s[sample_time_offset] * 1000, s[y_axis_offset+2])for s in group]}
                series.update(new_dict)
        elif average:
            y_axis_offset = samples["fields"].index(y + "_avg")
            groups = itertools.groupby(samples["results"], operator.itemgetter(node_id_offset))
            for k, group in groups:
                new_dict = {("Node " + str(k) + id_str + " avg"): [(s[sample_time_offset] * 1000, s[y_axis_offset])for s in group]}
                series.update(new_dict)
        else:
            y_axis_offset = samples["fields"].index(y)
            groups = itertools.groupby(samples["results"], operator.itemgetter(node_id_offset))
            for k, group in groups:
                new_dict = {("Node " + str(k) + id_str): [(s[sample_time_offset] * 1000, s[y_axis_offset])for s in group]}
                series.update(new_dict)

    chart_response = {
        "start": start_date*1000,
        "end": end_date*1000,
        "series": series
    }

    return jsonify(chart_response)

@app.route("/bg_data")
def get_latest_samples():
    fields = request.args.get("field")
    if fields is not None:
        fields = list(map(str, (y for y in fields.split("+"))))
        if fields[0] in "on":
            fields.remove("on")

    series = Samples.get_bg_samples(g.db, fields)

    # logging.info("series: {0}".format(series))
    chart_response = {
        "series": series
    }

    # logging.info("chart_response: {0}".format(chart_response))

    # prevent response from being sorted for soil moisture bar graph
    app.config['JSON_SORT_KEYS'] = False
    json = jsonify(chart_response)
    app.config['JSON_SORT_KEYS'] = True

    return json



@app.route("/database")
def get_database():
    return send_from_directory(os.path.dirname(__file__), "database.db")


# -----------------------------------------------


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        # logging.info("starting in demo mode")
        app.run(debug=True, host='0.0.0.0')
    else:
        with xbeecom(db_resource(app)) as xbee:
            app.run(debug=False, host='0.0.0.0')
