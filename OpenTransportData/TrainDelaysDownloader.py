#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 28 15:36:29 2021

@author: Clemens

Script to download and preprocess data for cancelled trains and train delays
from the open transport data Switzerland https://opentransportdata.swiss/de/
The script loads older data which is made available in an open google drive
(https://drive.google.com/drive/folders/1SVa68nJJRL3qgRSPKcXY7KuPN9MuHVhJ)
The script needs the path / name to a csv file with the google drive ids of the wanted zip-files
"""

#import libaries
import csv
import os
import sys
#Lib for downloading files from google drives
from googleDriveFileDownloader import googleDriveFileDownloader
import pandas as pd
import zipfile
from io import BytesIO
from sqlalchemy import create_engine

#check if debug mode then use testlist.csv
gettrace = getattr(sys, 'gettrace', None)
if gettrace():
    google_ids_file = './testlist.txt'
else:
    google_ids_file = sys.argv[1] #csv file with google drive ids


zip_filename = './tmp.zip' #tmp file for downloaded data
db_name = './trains.db' #sql-file for data export

#helper functions
def calculate_delays(df, arrival_delays):
    '''function to calculate trains delays from departure and arrival times'''

    #calc arrival delays or departure delays?
    if arrival_delays == True:
        time_prognosis = 'AN_PROGNOSE'
        time_real = 'ANKUNFTSZEIT'
        delay_calculated = 'AN_VERSPAETUNG'
    else:
        time_prognosis = 'AB_PROGNOSE'
        time_real = 'ABFAHRTSZEIT'
        delay_calculated = 'AB_VERSPAETUNG'
    
    df[time_real] = pd.to_datetime(df[time_real], format='%d.%m.%Y %H:%M')
    df[time_prognosis] = pd.to_datetime(df[time_prognosis], format='%d.%m.%Y %H:%M:%S')

    #floor to minutes, we measure only delays in minutes
    df[time_prognosis] = df[time_prognosis].dt.floor('Min')
    
    #Calculate delay convert to seconds and then to minutes (there is no way to do this directly)
    df[delay_calculated ] = ( df[time_prognosis] - df[time_real])

    #get index and values of train arrivals in advance (neg time difference)
    neg_index = df.loc[df[delay_calculated ] < pd.Timedelta(0)].index
    neg_values = df[delay_calculated ][neg_index]
    #shift time one day in future (not negative) convert to minutes in float and then substract minutes of one day
    neg_values = (((neg_values + pd.Timedelta(1, 'D')).dt.seconds / 60) - 1440)


    #get index and values of delays pos time difference convert to minutes
    pos_index = df.loc[df[delay_calculated ] >= pd.Timedelta(0)].index
    pos_values = df[delay_calculated ][pos_index]
    pos_values = ((pos_values.dt.seconds) / 60)

    #write into delay column
    df[delay_calculated ][pos_index] = pos_values
    df[delay_calculated ][neg_index] = neg_values
    df[delay_calculated ] = df[delay_calculated ].astype(int)
    
    return df

def write_to_sql(df, table, db):
    '''appends df to sqlite3 database'''
    #create sqlalchemy engine and connection
    try:
        sql_engine = create_engine(f'sqlite:///{db}', echo=True)
        with sql_engine.connect():
            df.to_sql(table, sql_engine, if_exists='append', index=False)
    except Exception() as e:
        print(e)


#load list of files in google_drive
with open(google_ids_file) as file:
    reader = csv.reader(file)
    google_files_list = list(reader)

#loop through id list and try to download files
for google_file in google_files_list:
    
    #loop for multiple download tries
    i = 0
    while i < 5:
        try:
            #load data from google drive to tmp.zip
            download_link = f"https://drive.google.com/uc?id={google_file[0]}&export=download"
            print(f"Download try {i+1} of 5 for Link: {download_link}")
            google_loader = googleDriveFileDownloader()
            
            #Download and verify download
            google_loader.downloadFile(download_link, zip_filename)
            zipfile.is_zipfile(zip_filename)
                       
            #read all csv files inside zip and extract the info wanted for train delays
            with zipfile.ZipFile(zip_filename, 'r') as zipObj:
                csv_files = zipObj.namelist()
                #extract month name from csv_files list
                csv_export_name = csv_files[0][:csv_files[0].find('/')]+'.csv'
                for csv_file in csv_files:
                    print(csv_file)
                    #read csv into bytes format
                    tmp_data = zipObj.read(csv_file)
    
                    #convert to dataframe
                    df_tmp = pd.read_csv(BytesIO(tmp_data), sep=';', parse_dates=False)
        
                    #only trains, no drive throughs
                    df_tmp = df_tmp.loc[(df_tmp['PRODUKT_ID'] == 'Zug') & (df_tmp['DURCHFAHRT_TF'] == False)]
                    df_tmp.drop(columns=['DURCHFAHRT_TF', 'PRODUKT_ID', 'UMLAUF_ID', 'ZUSATZFAHRT_TF', 'VERKEHRSMITTEL_TEXT', 'BETREIBER_ID', 'BETREIBER_ABK', 'LINIEN_ID'], inplace=True) 
            
                    #calculate delays first drop not available delay values
                    df_tmp.dropna(subset=['AN_PROGNOSE', 'AB_PROGNOSE'], inplace=True)
                    df_tmp = calculate_delays(df_tmp, True)
                    df_tmp = calculate_delays(df_tmp, False)

                    #table name is month
                    table_name = df_tmp['BETRIEBSTAG'].iloc[0][3:].replace('.','_')
                    
                    #add tmp data to dataframe
                    write_to_sql(df_tmp, table_name, db_name)
                
                #clear variables
                tmp_data = None
                df_tmp = None
            break
        except Exception as e:
            i += 1
            print(e)

#delete tmp file
try:
    os.remove(zip_filename)
except Exception as e:
    print(e)