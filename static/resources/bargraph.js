$(document).ready(function() {
    createChart({series: []}, "air_temp");
    $('#graph-container').highcharts().showLoading();

    initial_field = "air_temp";
	$.getJSON('/bg_data', {
		field: initial_field,
	}, function(data) {
		$('#graph-container').highcharts().hideLoading();
		createChart(data, initial_field);
	}).fail(function(faildata) {
		$('#graph-container').highcharts().hideLoading();
		console.log("fail",faildata)
	})
});

  $('button#new_graph').bind('click', function() {
	$('#graph-container').highcharts().showLoading();

    /*field = $('input[name="field"]:checked').map(function() {
			      return $(this).val();
		      }).toArray().join('+')*/
    field = $('input[name="field"]:checked').val();
	$.getJSON('/bg_data', {
		field: field
	}, function(data) {
		$('#graph-container').highcharts().hideLoading();
		createChart(data, field);
	}).fail(function(faildata) {
		$('#graph-container').highcharts().hideLoading();
		console.log("fail",faildata)
	})
});

function createChart(data, field) {
    field = field.split('+');
    categories = ['Node 1','Node 2','Node 3','Node 4','Node 5','Node 6','Node 7']
    if(field[0] === "air_temp") {
        title = "Air Temperature";
        f = function(value) { return Highcharts.numberFormat(value, 1) + " C"};
	} else if(field[0] === "soil_temp1") {
	    title = "Soil Temperature";
	    f = function(value) { return Highcharts.numberFormat(value, 1) + " C"};
	} else if(field[0] === "soil_moisture3") {
	    title = "Soil Moisture";
		f = function(value) { return Highcharts.numberFormat(value * 100, 2) + '% VWC'; };
	} else if(field[0] === "air_rh") {
	    title = "Relative Humidity";
		f = function(value) { return Highcharts.numberFormat(value, 2) + '%'; };
	} else if(field[0] === "soil_EC1" || field[0] === "soil_EC2") {
	    title = "Soil Electroconductivity";
		f = function(value) { return Highcharts.numberFormat(value, 2) + ' dS/m'; };
	} else if(field[0] === "soil_DP1" || field[0] === "soil_DP2") {
	    title = "Apparent Dielectric Permittivity";
		f = function(value) { return Highcharts.numberFormat(value, 0); };
	} else if(field[0] === "uvi") {
	    title = "UV Index";
		f = function(value) { return Highcharts.numberFormat(value, 0); };
	} else if(field[1] === "uva" || field[1] === "uvb") {
	    title = "Solar Irradience";
		f = function(value) { return Highcharts.numberFormat(value, 3) + " kW/m^2"; };
	} else if(field[0] === "wind_speed") {
	    title = "Wind Speed";
		f = function(value) { return Highcharts.numberFormat(value, 1) + " m/s"; };
		categories = ['Node 1','Node 4','Node 7'];
	} else if(field[0] === "wind_direction") {
	    title = "Wind Direction";
		categories = ['Node 1','Node 4','Node 7'];
		f = function(value)
		{
            var direction="";
		    var value = parseInt(value);
		    if(value<0)
		        return "No Direction (Wind Calm)";
		    else if (value <= 22)
		        direction = "N";
		    else if (value <= 67)
		        direction = "NE";
		    else if (value <= 112)
		        direction = "E";
		    else if (value <= 157)
		        direction = "SE";
		    else if (value <= 202)
		        direction = "S";
		    else if (value <= 247)
		        direction = "SW";
		    else if (value <= 292)
		        direction = "W";
		    else if (value <= 337)
		        direction = "NW";
		    else
		        direction = "N";
		    return direction + " (" + Highcharts.numberFormat(value, 0) + " deg)";
		};
	 }

	Highcharts.chart('graph-container', {
      chart: {
        type: 'column'
      },
      title: {
        text: title
      },
      xAxis: {
        categories: categories,
        crosshair: true
      },
        yAxis: {
            labels: {
                formatter: function () {
                    return f(this.value);
                }
            }
        },
      tooltip: {
        headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
        pointFormatter: function () {
         return '<tr><td style="color:' + this.series.color + ';padding:0">'+ this.series.name + '&nbsp</td>' +
         '<td style="padding:0"><b>' + f(this.y) + '</b></td></tr>';
        },
        footerFormat: '</table>',
        shared: true,
        useHTML: true
      },
      plotOptions: {
        column: {
          pointPadding: 0.2,
          borderWidth: 0
        }
      },
      series: $.map(data.series, function(value, key) {
			return {
				name: key,
				data: value,
				dataLabels: {
                  enabled: true,
                  align: 'center',
                  padding: 0,
                  color: '#777777',
                  format: '{point.y:.2f}', // one decimal
                  y: -5, // 10 pixels down from the top
                  style: {
                    fontSize: '9px',
                    fontFamily: 'Verdana, sans-serif'
                  }
                },
			};
		}),
    });
};