$(document).ready(function() {
	createChart({series: []}, "air_temp");
	$( "#max-min").prop('checked', false);
});

$('#datepicker').on('changeDate', function() {
    if(new Date($('input[name="start_date"]').val()).getTime() > new Date(2019, 3, 1, 0, 0, 0, 0).getTime())
    {
        $( "#soil-temp3-checkbox" ).hide();
        $( "#soil-temp3-checkbox").prop('checked', false);
        $("#soil-temp2-checkbox").css('margin-top', '10px');
    }
    else
    {
      $("#soil-temp2-checkbox").css('margin-top', '-5px');
        $( "#soil-temp3-checkbox" ).show();
    }
});

$('[name="average"]').click(function() {
    if($('#average-none').is(':checked'))
    {
        $( "#max-min-form-group" ).hide();
        $( "#max-min").prop('checked', false);
        $('[name="node"]').attr("type", "checkbox");
        $('[name="node"]').prop('checked', true);
    }
    else
    {
        $( "#max-min-form-group" ).show();
    }
  });

$("#max-min").click(function() {
    if($("#max-min").is(':checked'))
    {
        $('[name="node"]').attr("type", "radio");
        $('[name="node"]').prop('checked', false);
        $('#node-1').prop('checked', true);
    }
    else
    {
        $('[name="node"]').attr("type", "checkbox");
        $('[name="node"]').prop('checked', true);
    }
  });

$('[name="field-y"]').click(function() {
    if($("#field-y-soil-temp").is(':checked'))
    {
        $( "#soil-temp-options" ).show();
    }
    else
    {
        $( "#soil-temp-options" ).hide();
        $( "#field-y-soil-temp1").prop('checked', false);
        $( "#field-y-soil-temp2").prop('checked', false);
        $( "#field-y-soil-temp3").prop('checked', false);
    }

    if($("#field-y-solar-irradience").is(':checked'))
    {
        $( "#solar-irradience-options" ).show();
    }
    else
    {
        $( "#solar-irradience-options" ).hide();
        $( "#field-y-uva").prop('checked', false);
        $( "#field-y-uvb").prop('checked', false);
    }

    if($("#field-y-soil-moisture").is(':checked'))
    {
        $( "#soil-moisture-options" ).show();
    }
    else
    {
        $( "#soil-moisture-options" ).hide();
        $( "#field-y-soil-moisture1").prop('checked', false);
        $( "#field-y-soil-moisture2").prop('checked', false);
        $( "#field-y-soil-moisture3").prop('checked', false);
    }

    if($("#field-y-soil-EC").is(':checked'))
    {
        $( "#soil-EC-options" ).show();
    }
    else
    {
        $( "#soil-EC-options" ).hide();
        $( "#field-y-soil-EC1").prop('checked', false);
        $( "#field-y-soil-EC2").prop('checked', false);
    }

    if($("#field-y-soil-DP").is(':checked'))
    {
        $( "#soil-DP-options" ).show();
    }
    else
    {
        $( "#soil-DP-options" ).hide();
        $( "#field-y-soil-DP1").prop('checked', false);
        $( "#field-y-soil-DP2").prop('checked', false);
    }
  });

$('button#new_graph').bind('click', function() {
	$('#graph-container').highcharts().showLoading();

    field_y = $('input[name="field-y"]:checked').map(function() {
			      return $(this).val();
		      }).toArray().join('+')
	$.getJSON('/data', {
		start: new Date($('input[name="start_date"]').val()).getTime(),
		end: new Date($('input[name="end_date"]').val()).getTime(),
		nodes: $('input[name="node"]:checked').map(function() {
			        return this.id.split('-')[1];
		        }).toArray().join('+'),
		field_y: field_y,
		field_x: $('input[name="field-x"]:checked').val(),
		average: $('input[name="average"]:checked').val(),
		max_min: $("#max-min").is(':checked'),
	}, function(data) {
		$('#graph-container').highcharts().hideLoading();
		createChart(data, field_y);
	}).fail(function(faildata) {
		$('#graph-container').highcharts().hideLoading();
		console.log("fail",faildata)
	})
});

function createChart(data, field_y) {
    field_y = field_y.split('+');
	if(field_y[1] === "soil_moisture1" || field_y[1] === "soil_moisture2" || field_y[1] === "soil_moisture3") {
	    title = "Soil Moisture";
		f = function(value) { return Highcharts.numberFormat(value * 100, 2) + '% VWC'; };
	} else if(field_y[0] === "air_rh") {
	    title = "Relative Humidity";
		f = function(value) { return Highcharts.numberFormat(value, 2) + '%'; };
	} else if(field_y[1] === "soil_EC1" || field_y[1] === "soil_EC2") {
	    title = "Soil Electroconductivity";
		f = function(value) { return Highcharts.numberFormat(value, 2) + ' dS/m'; };
	} else if(field_y[1] === "soil_DP1" || field_y[1] === "soil_DP2") {
	    title = "Apparent Dielectric Permittivity";
		f = function(value) { return Highcharts.numberFormat(value, 0); };
	} else if(field_y[0] === "uvi") {
	    title = "UV Index";
		f = function(value) { return Highcharts.numberFormat(value, 0); };
	} else if(field_y[1] === "uva" || field_y[1] === "uvb") {
	    title = "Solar Irradience";
		f = function(value) { return Highcharts.numberFormat(value, 3) + " kW/m^2"; };
	} else if(field_y[0] === "wind_speed") {
	    title = "Wind Speed";
		f = function(value) { return Highcharts.numberFormat(value, 1) + " m/s"; };
	} else if(field_y[0] === "wind_direction") {
	    title = "Wind Direction";
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
	} else {
	    f = function(value) { return Highcharts.numberFormat(value, 1) + " C"};
	    if(field_y[0] === "air_temp")
	        title = "Air Temperature";
	    else
	        title = "Soil Temperature";

	}

	$('#graph-container').highcharts('StockChart', {

	  title: {
        text: title
      },
		yAxis: {
			labels: {
				formatter: function () {
					return f(this.value);
				}
			}
		},

		plotOptions: {
			series: {
				animation: false,
				dataGrouping: {
					groupPixelWidth: 5,
					smoothed: true
				}
			}
		},

		tooltip: {
			pointFormatter: function () {
				return '<span style="color:' + this.series.color + '">' + this.series.name + '</span>: <b>' + f(this.y) + '</b><br/>';
			},
		},


		series: $.map(data.series, function(value, key) {
			return {
				name: key,
				data: value
			};
		}),

	});
};
