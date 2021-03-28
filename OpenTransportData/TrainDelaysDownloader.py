#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 28 15:36:29 2021

@author: Clemens 

Script to download and preprocess data for cancelled trains and train delays
from the open transport data Switzerland https://opentransportdata.swiss/de/
The script loads older data which is made availble in an open google drive (https://drive.google.com/drive/folders/1SVa68nJJRL3qgRSPKcXY7KuPN9MuHVhJ)
The script needs the path / name to a csv file with the google drive ids of the wanted zip-files
"""

#import libaries
import csv
import os
import sys
#Lib for downloading files from google drives
from googleDriveFileDownloader import googleDriveFileDownloader
import pandas as pd
import numpy as np
from zipfile import ZipFile
from io import BytesIO


google_ids_file = sys.argv[1] #csv file with google drive ids
zip_filename = './tmp.zip' #tmp file for downloaded data
delays_zip = './delays.zip' #zip-file for train delay exoprt
delays_csv = 'delays.csv' #csv-file for train delay exoprt
cancelled_zip = './cancelled.zip' #zip-file for cancelled trains exoprt
cancelled_csv = 'cancelled.csv' #csv-file for cancelled trains exoprt


#helper functions for extracting the needed information
def extract_delays(df):
    '''function to extract neccesary information for train delays'''
    #Only entries where the real arrival times are available are uses
    #ignore cancelled trips and departure times
    df = df.loc[(df['FAELLT_AUS_TF'] == False) & (df['AN_PROGNOSE_STATUS'] == "REAL")
                , ['BETRIEBSTAG', 'BETREIBER_ABK', 'BETREIBER_NAME', 'LINIEN_ID', 'LINIEN_TEXT', 'HALTESTELLEN_NAME', 'ANKUNFTSZEIT', 'AN_PROGNOSE']]
    
    #Change Timestrings into datetime objects
    df['ANKUNFTSZEIT'] = pd.to_datetime(df['ANKUNFTSZEIT'], format='%d.%m.%Y %H:%M')
    df['AN_PROGNOSE'] = pd.to_datetime(df['AN_PROGNOSE'], format='%d.%m.%Y %H:%M:%S')

    #floor to minutes, we measure only delays in minutes
    df['AN_PROGNOSE'] = df['AN_PROGNOSE'].dt.floor('Min')
    
    #Calculate delay convert to seconds and then to minutes (there is no way to do this directly)
    df['VERSPAETUNG'] = (df['AN_PROGNOSE'] - df['ANKUNFTSZEIT'])

    #get index and values of train arrivals in advance (neg time difference)
    neg_index = df.loc[df['VERSPAETUNG'] < pd.Timedelta(0)].index
    neg_values = df['VERSPAETUNG'][neg_index]
    #shift time one day in future (not negative) convert to minutes in float and then substract minutes of one day
    neg_values = (((neg_values + pd.Timedelta(1, 'D')).dt.seconds / 60) - 1440)


    #get index and values of delays pos time difference convert to minutes
    pos_index = df.loc[df['VERSPAETUNG'] >= pd.Timedelta(0)].index
    pos_values = df['VERSPAETUNG'][pos_index]
    pos_values = ((pos_values.dt.seconds) / 60)

    #write into delay column
    df['VERSPAETUNG'][pos_index] = pos_values
    df['VERSPAETUNG'][neg_index] = neg_values
    df['VERSPAETUNG'] = df['VERSPAETUNG'].astype(int)
    
    return df


def extract_cancels(df):
    '''function to extract neccesary information for cancelled'''
    #For cancelled trains we do not need the times prognosis, also we drop duplicate lines
    df = df.loc[:, ['FAHRT_BEZEICHNER','BETRIEBSTAG', 'BETREIBER_ABK', 'BETREIBER_NAME', 'LINIEN_ID', 'LINIEN_TEXT', 'FAELLT_AUS_TF', 'HALTESTELLEN_NAME']]
    df.drop_duplicates(subset=['FAHRT_BEZEICHNER', 'LINIEN_ID', 'LINIEN_TEXT', 'BETREIBER_ABK', 'FAELLT_AUS_TF'], inplace=True)
    #keep only Linien ID and not Fahrt Bezeichner for memory reasons
    df.drop(columns=['FAHRT_BEZEICHNER'], inplace = True)
    
    return df


#load list of files in google_drive
with open(google_ids_file) as file:
    reader = csv.reader(file)
    google_files_list = list(reader)

#create empty dataframes
df_delays = pd.DataFrame()
df_cancelled = pd.DataFrame()

#loop through id list and try to download files
for google_file in google_files_list:
    #while loop for multiple download tries
    i = 0
    while i < 10:
        print(f"Download try {i+1} of 10" )
        #load data from google drive to tmp.zip
        download_link = f"https://drive.google.com/uc?id={google_file[0]}&export=download"
        print(download_link)
        google_loader = googleDriveFileDownloader()
        google_loader.downloadFile(download_link, zip_filename)
    
        #read all csv files inside zip and extract the info wanted for train delays
        try:
            with ZipFile(zip_filename, 'r') as zipObj:
                csv_files = zipObj.namelist()
                for csv_file in csv_files:
                    print(csv_file)
                    #read csv into bytes format
                    tmp_data = zipObj.read(csv_file)
        
                    #convert to dataframe
                    df_tmp = pd.read_csv(BytesIO(tmp_data), sep=';', parse_dates=False)
        
                    #only trains, no drive throughs, no station names and no departure times
                    df_tmp = df_tmp.loc[(df_tmp['PRODUKT_ID'] == 'Zug') & (df_tmp['DURCHFAHRT_TF'] == False),
                            ['FAHRT_BEZEICHNER', 'BETRIEBSTAG', 'BETREIBER_ABK', 'BETREIBER_NAME', 'LINIEN_ID', 'LINIEN_TEXT', 'FAELLT_AUS_TF', 'ANKUNFTSZEIT', 'AN_PROGNOSE', 'AN_PROGNOSE_STATUS', 'HALTESTELLEN_NAME']]
        
                    #extract data for delays and append to dataframe
                    df_delays = df_delays.append(extract_delays(df_tmp))
        
                    #extract data for cancelled trains and append to dataframe
                    df_cancelled = df_cancelled.append(extract_cancels(df_tmp))
            #end loop
            break
        except:
                    i += 1
                
#delete tmp file
os.remove(zip_filename)

#save DataFrame to csv for further usage
df_delays.to_csv(delays_zip, index=False, compression={'method' : 'zip', 'archive_name' : delays_csv})
df_cancelled.to_csv(cancelled_zip, index=False, compression={'method' : 'zip', 'archive_name' : cancelled_csv})