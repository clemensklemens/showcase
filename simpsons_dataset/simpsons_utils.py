#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 19 15:34:57 2021

@author: clemens

File contains utility functions for simpsons machine learning project
"""

import numpy as np
import glob
from skimage import io, transform, exposure, color
import matplotlib.pyplot as plt
import re

def create_train_image_list(path, character_list):
   #Returns a list with path and names of all image files, label is the subfolder
    image_files = []
    labels = []

    #Iterate over dict
    for idx, names in enumerate(character_list):
        for image_file in glob.glob(f"{path}/{names}/*.jpg"):
            image_files.append(image_file)
            labels.append(idx)
    
    image_files = np.asarray(image_files)        
    labels = np.asarray(labels)
    return image_files, labels



def create_test_image_list(path):
   #Returns a list with path and names to all files given folder, no labels are provided
    #Iterate over files in folder
    image_files = [image_file for image_file in glob.glob(f"{path}/*.jpg")]
    
    #strip path from image list and use regex to remove the trailing number and file type
    true_labels = [re.split(r"_\d+.jpg", img[len(path):])[0] for img in image_files]
    return np.asarray(image_files), np.asarray(true_labels)    



def make_chunks(image_list, y, chunk_size=32):
    #divide a np.array into equal sized subarrays
    X_chunks = np.split(image_list, range(chunk_size, image_list.shape[0], chunk_size))
    y_chunks = np.split(y, range(chunk_size, y.shape[0], chunk_size))
    return X_chunks, y_chunks


def load_transform_images(image_list, settings_dict):
    #Function to load and transform images from an image_list according to settings
    images = []
    for img in image_list:
        tmp_img = io.imread(img)
        tmp_img = transform.resize(tmp_img, settings_dict["size"])
        if settings_dict["grey"] == True: #make greyscale
            tmp_img = color.rgb2gray(tmp_img)
        if settings_dict["gamma_correction"] == True: #change gamma
            tmp_img = exposure.adjust_gamma(tmp_img, gamma=0.9, gain=1.1)
        if settings_dict["contrast_correction"] == True: #change contrast
            min_int = tmp_img.min()
            max_int = tmp_img.max()
            tmp_img = exposure.rescale_intensity(tmp_img, in_range=(min_int, max_int))
        images.append(tmp_img / 255)
    return np.asarray(images)


def show_random_images(image_files, labels, character_list, settings_dict=None):
    plt.figure(1 , figsize = (15 , 9))
    for i in range(8):
        r = np.random.randint(0 , len(image_files) , 1)[0]
        plt.subplot(2 , 4 , i+1)
        plt.subplots_adjust(hspace = 0.2 , wspace = 0.1)
        if settings_dict == None:
            plt.imshow(io.imread(image_files[r]))
        else:
            tmp_img = load_transform_images([image_files[r]], settings_dict)
            tmp_img = tmp_img[0] * 255 #255 because load transform directly scales the images
            plt.imshow(tmp_img, cmap='Greys_r')
        plt.title(f'{character_list[labels[r]]}')
        plt.axis('off')
    plt.show()