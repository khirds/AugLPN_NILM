from Arguments import *
from Logger import log
from tensorflow.keras.models import Model  # Input,
from tensorflow.keras.layers import MaxPooling1D,Dense, Dropout, Conv2D, GlobalMaxPooling2D, Flatten, Reshape, Lambda, dot, \
    UpSampling2D, Add, Concatenate, Activation, concatenate, Conv1D, BatchNormalization, add
from tensorflow.keras.utils import plot_model  
import numpy as np
import tensorflow.keras.backend as K
import os
from typing import List, Tuple
import tensorflow.keras.backend as K
# #import keras.layers
# from tensorflow.keras import optimizers
# from tensorflow.keras.engine.topology import Layer
# import tensorflow as tf # if tensorflow 1
# import tensorflow.compat.v1 as tf # if using tensorflow 2
# tf.disable_v2_behavior()
import tensorflow._api.v2.compat.v1 as tf

tf.disable_v2_behavior()

########################
import h5py
import argparse
from tensorflow.keras.layers import GlobalAveragePooling2D, GlobalMaxPooling2D, Reshape, Dense, multiply, Permute, \
    Concatenate, Conv2D, Add, Activation, Lambda
from tensorflow.keras import backend as K
from tensorflow.keras.activations import sigmoid

# import tensorflow  as tf

# Model setting begin, used in Sequence to point Learning based on bidirectional dilated residual network for nilm
nb_filters = 128
filter_length = 3
dilations = [1, 2, 4, 8, 16, 32, 64, 128]
dropout = 0.3

def AlexNet_model(appliance, input_tensor, window_length, transfer_dense=False, transfer_cnn=False,
              cnn='fridge', pretrainedmodel_dir='./models/', n_dense=1):
    reshape = Reshape((window_length, 1), )(input_tensor)
    cnn1 = Conv1D(filters=128,
                  kernel_size=5,
                  strides=1,
                  activation='relu',
                  )(reshape)
    max1 = MaxPooling1D(pool_size=2, strides=2)(cnn1)
    cnn2 = Conv1D(filters=128,
                  kernel_size=5,
                  strides=1,
                  activation='relu',
                  )(max1)
    cnn3 = Conv1D(filters=128,
                  kernel_size=5,
                  strides=1,
                  activation='relu',
                  )(cnn2)
    max2 = MaxPooling1D(pool_size=2, strides=2)(cnn3)
    cnn4 = Conv1D(filters=256,
                  kernel_size=10,
                  strides=1,
                  activation='relu',
                  )(max2)
    cnn5 = Conv1D(filters=256,
                  kernel_size=10,
                  strides=1,
                  activation='relu',
                  )(cnn4)
    max3 = MaxPooling1D(pool_size=2, strides=2)(cnn5)
    cnn6 = Conv1D(filters=256,
                  kernel_size=5,
                  strides=1,
                  padding='same',
                  activation='relu',
                  )(max3)
    cnn7 = Conv1D(filters=256,
                  kernel_size=5,
                  strides=1,
                  padding='same',
                  activation='relu',
                  )(cnn6)
    flat = Flatten(name='flatten')(cnn7)

    d = Dense(256, activation='sigmoid', name='dense1')(flat)
    d = Dense(512, activation='sigmoid', name='dense2')(d)
    d = Dense(1024, activation='sigmoid', name='dense3')(d)
    d_out = Dense(1, activation='linear', name='output')(d)

    model = Model(inputs=input_tensor, outputs=d_out)
    # Model setting done
    ####model structure done!
    ##############################
    # session = K.get_session() # For Tensorflow 1
    session = tf.keras.backend.get_session()  # For Tensorflow 2
    #   The name tf.keras.backend.get_session is deprecated. Please use tf.compat.v1.keras.backend.get_session instead.
    ##############################
    # For transfer learning
    if transfer_dense:
        log("Transfer learning...")
        log("...loading an entire pre-trained model")
        weights_loader(model, pretrainedmodel_dir + '/cnn_s2p_' + appliance + '_pointnet_model')
        model_def = model
    elif transfer_cnn and not transfer_dense:
        log("Transfer learning...")
        log('...loading a ' + appliance + ' pre-trained-cnn')
        cnn_weights_loader(model, cnn, pretrainedmodel_dir)
        model_def = model
        for idx, layer1 in enumerate(model_def.layers):
            if hasattr(layer1, 'kernel_initializer') and 'conv2d' not in layer1.name and 'cnn' not in layer1.name:
                log('Re-initialize: {}'.format(layer1.name))
                layer1.kernel.initializer.run(session=session)

    elif not transfer_dense and not transfer_cnn:
        log("Standard training...")
        log("...creating a new model.")
        model_def = model
    else:
        raise argparse.ArgumentTypeError('Model selection error.')
    # Printing, logging and plotting the model
    # print_summary(model_def)
    model_def.summary()
    # plot_model(model, to_file='./model.png', show_shapes=True, show_layer_names=True, rankdir='TB')

    # Adding network structure to both the log file and output terminal
    files = [x for x in os.listdir('./') if x.endswith(".log")]
    with open(max(files, key=os.path.getctime), 'a') as fh:
        # Pass the file handle in as a lambda function to make it callable
        model_def.summary(print_fn=lambda x: fh.write(x + '\n'))
    return model_def
# --------------------------------


def print_attrs(name, obj):
    print(name)
    for key, val in obj.attrs.items():
        print("    %s: %s" % (key, val))


def cnn_weights_loader(model_to_fill, cnn_appliance, pretrainedmodel_dir):
    log('Loading cnn weights from ' + cnn_appliance)
    weights_path = pretrainedmodel_dir + '/cnn_s2p_' + cnn_appliance + '_pointnet_model' + '_weights.h5'
    if not os.path.exists(weights_path):
        print('The directory does not exist or you do not have the files for trained model')

    f = h5py.File(weights_path, 'r')
    log(f.visititems(print_attrs))
    layer_names = [n.decode('utf8') for n in f.attrs['layer_names']]
    for name in layer_names:
        if 'conv2d_' in name or 'cnn' in name:
            g = f[name]
            weight_names = [n.decode('utf8') for n in g.attrs['weight_names']]
            if len(weight_names):
                weight_values = [g[weight_name] for weight_name in weight_names]

            model_to_fill.layers[int(name[-1]) + 1].set_weights(weight_values)
            log('Loaded cnn layer: {}'.format(name))

    f.close()
    print('Model loaded.')


def weights_loader(model, path):
    log('Loading cnn weights from ' + path)
    model.load_weights(path + '_weights.h5')
