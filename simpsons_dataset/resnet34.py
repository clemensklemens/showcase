#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 27 14:21:10 2021

@author: clemens

File contains a function to creat a resnet34 CNN model
And a class with definition of a custom layer used by the model
Just call resnet34()
"""

#Keras
#import tensorflow as tf
from tensorflow import keras

#Definition of residual layer class used by model defintion later
class ResidualUnit(keras.layers.Layer):
    def __init__(self, filters, strides=1, activation="relu", **kwargs):
        super().__init__(**kwargs) #load from super class
        self.activation = keras.activations.get(activation)
        #create normal layers
        self.main_layers = [
            keras.layers.Conv2D(filters, 3, strides=strides, padding="same", use_bias=False)
          , keras.layers.BatchNormalization()
          , self.activation
          , keras.layers.Conv2D(filters, 3, strides=1, padding="same", use_bias=False)
          , keras.layers.BatchNormalization()
          ]
        #create skip layers (if stride > 1)
        self.skip_layers = []
        if strides > 1:
            self.skip_layers = [
                  keras.layers.Conv2D(filters, 1, strides=strides, padding="same", use_bias=False)
                , keras.layers.BatchNormalization()
                ]
        
    def call(self, inputs):
        Z = inputs
        #Feed inputs to normal layers
        for layer in self.main_layers:
            Z = layer(Z)
        #feed input to skip layers
        skip_Z = inputs
        for layer in self.skip_layers:
            skip_Z = layer(skip_Z)
        #combine
        return self.activation(Z + skip_Z)
         
    #update does not work
    def get_config(self):
        config = super().get_config()
        config.update({
            'weights': self.weights,
            #'skip_layers' : self.skip_layers,
            'activation' : self.activation,
        })
        return config

#function for model declaration
def resnet34(settings_dict):
    #input size, adapt to greyscale or RGB
    if settings_dict['grey'] == True:
        shape = [settings_dict['size'][0],settings_dict['size'][1], 1]
    else:
        shape = [settings_dict['size'][0],settings_dict['size'][1], 3]
        
    #model
    model = keras.models.Sequential()
    model.add(keras.layers.Conv2D(64, 7, strides=2, input_shape=shape, padding="same", use_bias=False))
    model.add(keras.layers.BatchNormalization())
    model.add(keras.layers.Activation("relu"))
    model.add(keras.layers.MaxPool2D(pool_size=3, strides=2, padding="same"))
    #add residual layers
    prev_filters = 64
    for filters in [64] * 3 + [128] * 4 + [256] * 6 + [512] * 3:
        strides = 1 if filters == prev_filters else 2
        model.add(ResidualUnit(filters, strides=strides))
        prev_filters = filters
    model.add(keras.layers.MaxPool2D(pool_size=3, strides=2, padding="same"))
    model.add(keras.layers.GlobalAveragePooling2D())
    model.add(keras.layers.Flatten())
    model.add(keras.layers.Dense(20, activation="softmax"))
    
    return model