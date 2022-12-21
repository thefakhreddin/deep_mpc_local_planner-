# -*- coding: utf-8 -*-
"""deep_mpc_trainer.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Fr4t_DqjNRAefwJUxOz9Hrlpm8qRNnF-
"""

import csv
import numpy as np
import pandas as pd
import random

import tensorflow as tf
from tensorflow import keras
from keras.models import Sequential, Model, load_model
from keras.layers import Dense, LSTM, Dropout, Input, Concatenate, Normalization

FOLDER_INDEX = 7
SECOND_INDEX = ''
PLAN_LENGTH = 50
DATASET_ADDRESS = f'drive/MyDrive/deepMPCDataset/log_{FOLDER_INDEX}/{SECOND_INDEX}'

cmdVel = pd.read_csv(f'{DATASET_ADDRESS}/cmd_vel_log.csv', delimiter=',').values
heading = pd.read_csv(f'{DATASET_ADDRESS}/heading.csv', delimiter=',').values
planX = pd.read_csv(f'{DATASET_ADDRESS}/global_plan_x_log.csv', delimiter=',', names=list(range(100)), header=None).values
planY = pd.read_csv(f'{DATASET_ADDRESS}/global_plan_y_log.csv', delimiter=',', names=list(range(100)), header=None).values

print("current data size: ")
print(cmdVel.shape, planX.shape, planY.shape, heading.shape)
len = np.amin([cmdVel.shape[0], planX.shape[0], planY.shape[0], heading.shape[0]])
cmdVel = cmdVel[:len]
heading = heading[:len]
planX = planX[:len]
planY = planY[:len]
print("reduced to: ")
print(cmdVel.shape, planX.shape, planY.shape, heading.shape)

planX = planX[:,:PLAN_LENGTH]
planY = planY[:,:PLAN_LENGTH]

def emptyRows(arr):
  delList = []
  for r, row in enumerate(arr):
    if np.any(np.isnan(row)):
      delList += [r]
  return delList

delList1 = emptyRows(planX)
delList2 = emptyRows(planY)
assert delList1 == delList2

planX = np.delete(planX, delList1, axis = 0)
planY = np.delete(planY, delList1, axis = 0)
cmdVel = np.delete(cmdVel, delList1, axis = 0)
heading = np.delete(heading, delList1, axis = 0)

print(f'deleting NaNs; size reduced to {planX.shape[0]}')

assert not np.any(np.isnan(planX))
assert not np.any(np.isnan(planY))
assert not np.any(np.isnan(cmdVel))
assert not np.any(np.isnan(heading))

print("data range:")
print(planX.min().round(5), planX.max().round(5))
print(planY.min().round(5), planY.max().round(5))
print("-------")
for i in range(cmdVel.shape[1]):
  print(cmdVel[:,i].min().round(5), cmdVel[:,i].max().round(5))
print("-------")
for i in range(heading.shape[1]):
  print(heading[:,i].min().round(5), heading[:,i].max().round(5))

plan = np.stack([planX, planY], axis=2)

plan = np.concatenate([plan, planTmp], axis=0)
heading = np.concatenate([heading, headingTmp], axis=0)
cmdVel = np.concatenate([cmdVel, cmdVelTmp], axis=0)

tf.convert_to_tensor(heading)

tf.convert_to_tensor(cmdVel)

tf.convert_to_tensor(plan)

print(f"input shape: {plan.shape, heading.shape}, output shape {cmdVel.shape}")

validationLength = int(plan.shape[0]*0.05)
print(f'validation length: {validationLength}')

planNormalizer = Normalization()
headingNormalizer = Normalization()

planNormalizer.adapt(plan)
headingNormalizer.adapt(heading)

planInput = Input((None, 2))
headingInput = Input((2,))

planNormalized = planNormalizer(planInput)
headingNormalized = headingNormalizer(headingInput)

planLatent = LSTM(32, input_shape=(None, 2), activation='tanh')(planNormalized)
planLatent = Dense(16, activation='tanh')(planLatent)

concatLayer = Concatenate()([planLatent, headingNormalized])

mergedLayer = Dense(16, activation='tanh')(concatLayer)
mergedLayer = Dropout(0.1)(mergedLayer)
mergedLayer = Dense(8, activation='tanh')(mergedLayer)
output = Dense(2, activation='tanh')(mergedLayer)

model = Model(inputs = [planInput, headingInput], outputs = output)

model.compile(loss='mse',
              optimizer = tf.keras.optimizers.SGD(learning_rate=1e-2, decay=1e-6, momentum=0.9, nesterov=True),
              metrics=['accuracy'])

model.summary()
tf.keras.utils.plot_model(model, to_file='model.png', show_shapes=True)

model_checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
    filepath=f'{DATASET_ADDRESS}/checkpoint',
    save_weights_only=False,
    monitor='val_loss',
    mode='min',
    save_best_only=True)

model.fit(
    x=[plan[:-validationLength], heading[:-validationLength]],
    y=cmdVel[:-validationLength],
    epochs=60,
    batch_size=256,
    validation_split=0.2,
    callbacks=[model_checkpoint_callback]
)

q = model.evaluate(x=[plan[-validationLength:], heading[-validationLength:]],
    y=cmdVel[-validationLength:],
    batch_size=128)
q = int(np.array(q).round(2)[1]*100)
print(f"evaluation accurecy: {q}%")

model.save(filepath = f"{DATASET_ADDRESS}/deepMPCModel{q}.h5", overwrite= True, include_optimizer=True)

model = load_model(f"{DATASET_ADDRESS}/deepMPCModel{q}.h5")

i = random.randint(0,plan.shape[0]-1)
vel = model.predict([plan[None,i], heading[None,i]])
print(f"sample predicted output: {vel}")