"""
Simple plot of 2D data
----------------------

This is an example of how to download and
plot ceiliometer data from the SGP site
over Oklahoma.

"""

import matplotlib.pyplot as plt
import act
import os

# Place your username and token here
username = os.getenv('ARM_USERNAME')
token = os.getenv('ARM_PASSWORD')

act.discovery.download_data(username, token, 'sgpceilC1.b1', '2017-01-14', '2017-01-19')

ceil_ds = act.io.armfiles.read_netcdf('sgpceilC1.b1/*')
ceil_ds = act.corrections.ceil.correct_ceil(ceil_ds, -9999.0)
display = act.plotting.TimeSeriesDisplay(ceil_ds, subplot_shape=(1,), figsize=(15, 5))
display.plot('backscatter', subplot_index=(0,))
plt.show()