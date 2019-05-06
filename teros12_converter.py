import math


def calculate_vwc(adc_counts):
    return (0.0003879 * adc_counts) - 0.6956


def calculate_dp(adc_counts):
    return 1.112 * math.pow(10, -18) * math.pow(adc_counts, 5.607)
