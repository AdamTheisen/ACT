"""
Script for downloading data from ARM's Live Data Webservice

"""

import json
import os
from datetime import timedelta
import requests
import textwrap
import warnings

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib import Request, urlopen

from act.utils import date_parser


def download_arm_data(username, token, datastream, startdate, enddate, time=None, output=None):
    """
    This tool will help users utilize the ARM Live Data Webservice to download
    ARM data.

    Parameters
    ----------
    username : str
        The username to use for logging into the ADC archive.
    token : str
        The access token for accessing the ADC archive.
    datastream : str
        The name of the datastream to acquire.
    startdate : str
        The start date of the data to acquire. Formats accepted are
        YYYY-MM-DD, DD.MM.YYYY, DD/MM/YYYY, YYYYMMDD, YYYY/MM/DD or
        any of the previous formats with THH:MM:SS added onto the end
        (ex. 2020-09-15T12:00:00).
    enddate : str
        The end date of the data to acquire. Formats accepted are
        YYYY-MM-DD, DD.MM.YYYY, DD/MM/YYYY, YYYYMMDD or YYYY/MM/DD, or
        any of the previous formats with THH:MM:SS added onto the end
        (ex. 2020-09-15T13:00:00).
    time: str or None
        The specific time. Format is HHMMSS. Set to None to download all files
        in the given date interval.
    output : str
        The output directory for the data. Set to None to make a folder in the
        current working directory with the same name as *datastream* to place
        the files in.

    Returns
    -------
    files : list
        Returns list of files retrieved

    Notes
    -----
    This programmatic interface allows users to query and automate
    machine-to-machine downloads of ARM data. This tool uses a REST URL and
    specific parameters (saveData, query), user ID and access token, a
    datastream name, a start date, and an end date, and data files matching
    the criteria will be returned to the user and downloaded.

    By using this web service, users can setup cron jobs and automatically
    download data from /data/archive into their workspace. This will also
    eliminate the manual step of following a link in an email to download data.
    All other data files, which are not on the spinning
    disk (on HPSS), will have to go through the regular ordering process.
    More information about this REST API and tools can be found on `ARM Live
    <https://adc.arm.gov/armlive/#scripts>`_.

    To login/register for an access token click `here
    <https://adc.arm.gov/armlive/livedata/home>`_.

    Author: Michael Giansiracusa
    Email: giansiracumt@ornl.gov

    Examples
    --------
    This code will download the netCDF files from the sgpmetE13.b1 datastream
    and place them in a directory named sgpmetE13.b1. The data from 14 Jan to
    20 Jan 2017 will be downloaded. Replace *userName* and *XXXXXXXXXXXXXXXX*
    with your username and token for ARM Data Discovery. See the Notes for
    information on how to obtain a username and token.

    .. code-block:: python

        act.discovery.download_data(
            "userName", "XXXXXXXXXXXXXXXX", "sgpmetE13.b1", "2017-01-14", "2017-01-20"
        )

    """
    # default start and end are empty
    start, end = '', ''
    # start and end strings for query_url are constructed
    # if the arguments were provided
    if startdate:
        start_datetime = date_parser(startdate, return_datetime=True)
        start = start_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        start = f'&start={start}'
    if enddate:
        end_datetime = date_parser(enddate, return_datetime=True)
        # If the start and end date are the same, and a day to the end date
        if start_datetime == end_datetime:
            end_datetime += timedelta(hours=23, minutes=59, seconds=59)
        end = end_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        end = f'&end={end}'
    # build the url to query the web service using the arguments provided
    query_url = (
        'https://adc.arm.gov/armlive/data/query?' + 'user={0}&ds={1}{2}{3}&wt=json'
    ).format(':'.join([username, token]), datastream, start, end)

    headers = {
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
    }

    req = Request(query_url, None, headers)
    # get url response, read the body of the message,
    # and decode from bytes type to utf-8 string
    response_body = urlopen(req).read().decode('utf-8')
    # if the response is an html doc, then there was an error with the user
    if response_body[1:14] == '!DOCTYPE html':
        raise ConnectionRefusedError('Error with user. Check username or token.')

    # parse into json object
    response_body_json = json.loads(response_body)

    # construct output directory
    if output:
        # output files to directory specified
        output_dir = os.path.join(output)
    else:
        # if no folder given, add datastream folder
        # to current working dir to prevent file mix-up
        output_dir = os.path.join(os.getcwd(), datastream)

    # not testing, response is successful and files were returned
    if response_body_json is None:
        print('ARM Data Live Webservice does not appear to be functioning')
        return []

    num_files = len(response_body_json['files'])
    file_names = []
    if response_body_json['status'] == 'success' and num_files > 0:
        for fname in response_body_json['files']:
            if time is not None:
                if time not in fname:
                    continue
            # construct link to web service saveData function
            save_data_url = (
                'https://adc.arm.gov/armlive/data/' + 'saveData?user={0}&file={1}'
            ).format(':'.join([username, token]), fname)
            req_save = Request(save_data_url, None, headers)
            output_file = os.path.join(output_dir, fname)
            # make directory if it doesn't exist
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)
            # create file and write bytes to file
            with open(output_file, 'wb') as open_bytes_file:
                data = urlopen(req_save).read()
                if 'This data file is not available' in str(data):
                    print(fname + ' is not available for download')
                    continue
                else:
                    print(f'[DOWNLOADING] {fname}')
                    open_bytes_file.write(data)
            file_names.append(output_file)
        # Get ARM DOI and print it out
        doi = get_arm_doi(
            datastream, start_datetime.strftime('%Y-%m-%d'), end_datetime.strftime('%Y-%m-%d')
        )
        print('\nIf you use these data to prepare a publication, please cite:\n')
        print(textwrap.fill(doi, width=80))
        print('')
    else:
        print(
            'No files returned or url status error.\n'
            'Check datastream name, start, and end date. \n'
        )
        if datastream.split('.')[-1] == 'a0':
            print(
                '---------------------ATTENTION--------------------\n',
                'ARM does not generally make a0-level data discoverable\n',
                'Please reach out through the ARM Help link to request access',
            )

    return file_names


def download_arm_data_mod(username, token, file_list, variables=None, filetype='cdf', output=None):
    """
    This function allows for downloading ARM data from ARM's data discovery mod API:
    https://adc.arm.gov/armlive/

    This function will then provide a concatenated file of the file list in csv or
    cdf file format with all variables or user provided variables.

    Parameters
    ----------
    username : str
        ARM username.
    token : str
        ARM user token.
    file_list : list
        A list of files by datetime of the same datastream to concatenate.
    variables : list
        A list of desired variables that exist in the datastream.
        Default is None and will provide all variables.
    file_type : str
        File type to download file as. Valid options are 'csv' and 'cdf'.
        Default is 'cdf'
    output : str
        The output directory for the data. Set to None to make a folder in the
        current working directory with the same name as filename to place
        the files in.

    Returns
    -------
    filename : str
        Concatenated filename
    """
    if variables is not None:
        variables_str = ",".join(variables)
        url = f'https://adc.arm.gov/armlive/mod?user={username}:{token}&variables={variables_str}&wt={filetype}'
    else:
        url = f'https://adc.arm.gov/armlive/mod?user={username}:{token}&wt={filetype}'
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers, data=json.dumps(file_list))

    if response.status_code == 200:
        # Save the response content to a file
        filename = response.headers.get('Content-Disposition').split('filename=')[1]
        filename = filename.replace('"', '')

        if output is not None:
            # output files to directory specified
            output_dir = os.path.join(output)
        else:
            # if no folder given, set current directory as folder
            output_dir = os.getcwd()

        # make directory if it doesn't exist and its a user provided folder.
        if not os.path.isdir(output_dir) and output is not None:
            os.makedirs(output_dir)

        output_file = os.path.join(output_dir, filename)

        with open(output_file, 'wb') as file:
            file.write(response.content)

        print(f"File saved as {filename}")
        return filename
    else:
        warnings.warn(
            'No files returned or url status error.\n'
            'Check if username, token, file list are valid. \n',
            UserWarning,
        )
        return


def get_arm_doi(datastream, startdate, enddate):
    """
    This function will return a citation with DOI, if available, for specified
    datastream and date range

    Parameters
    ----------
    datastream : str
        The name of the datastream to get a DOI for.  This must be ARM standard names
    startdate : str
        Start date for the citation in the format YY-MM-DD
    enddate : str
        End date for the citation in the format YY-MM-DD

    Returns
    -------
    doi : str
        Returns the citation as a string

    """
    headers = {
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
    }
    # Get the DOI information
    doi_url = (
        'https://adc.arm.gov/citationservice/citation/datastream?id='
        + datastream
        + '&citationType=apa'
    )
    doi_url += '&startDate=' + startdate
    doi_url += '&endDate=' + enddate
    try:
        doi = requests.get(url=doi_url, headers=headers)
    except ValueError as err:
        return "Webservice potentially down or arguments are not valid: " + err

    if len(doi.text) > 0:
        doi = doi.json()['citation']
    else:
        doi = 'Please check your arguments. No DOI Found'

    return doi
