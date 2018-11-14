import tensorflow as tf
import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
from tensorflow.examples.tutorials.mnist import input_data
import getConfig
gConfig={}
gConfig=getConfig.get_config(config_file='config.ini')
#定义训练数据的维度
seq_len=gConfig['seqlen']

#读取数据
def read_data(source_file):
    data=pd.read_csv(source_file,encoding='utf-8')
    dataset=data.values
    return dataset
dataset = read_data(gConfig['input_file'])

tf.reset_default_graph()

batch_size = 64
X_in = tf.placeholder(dtype=tf.float32, shape=[None, seq_len], name='X')
Y = tf.placeholder(dtype=tf.float32, shape=[None, seq_len], name='Y')
Y_flat = tf.reshape(Y, shape=[-1, seq_len * 1])
keep_prob = tf.placeholder(dtype=tf.float32, shape=(), name='keep_prob')

dec_in_channels = 1
#encoder输出的数据维度
n_latent = gConfig['enc_out_len']
reshaped_dim = [-1, 7, 7, dec_in_channels]
inputs_decoder = 49 * dec_in_channels // 2

#定义激活函数

def lrelu(x, alpha=0.3):
    return tf.maximum(x, tf.multiply(x, alpha))
#定义编码机
def encoder(X_in, keep_prob):
    activation = lrelu
    with tf.variable_scope("encoder", reuse=None):
        X = tf.reshape(X_in, shape=[-1, seq_len, 1, 1])
        x = tf.layers.conv2d(X, filters=64, kernel_size=4, strides=2, padding='same', activation=activation)
        x = tf.nn.dropout(x, keep_prob)
        x = tf.layers.conv2d(x, filters=64, kernel_size=4, strides=2, padding='same', activation=activation)
        x = tf.nn.dropout(x, keep_prob)
        x = tf.layers.conv2d(x, filters=64, kernel_size=4, strides=1, padding='same', activation=activation)
        x = tf.nn.dropout(x, keep_prob)
        x = tf.contrib.layers.flatten(x)
        mn = tf.layers.dense(x, units=n_latent)
        sd       = 0.5 * tf.layers.dense(x, units=n_latent)
        epsilon = tf.random_normal(tf.stack([tf.shape(x)[0], n_latent]))
        z  = mn + tf.multiply(epsilon, tf.exp(sd))
        return z, mn, sd

#定义解码机
def decoder(sampled_z, keep_prob):
    with tf.variable_scope("decoder", reuse=None):
        x = tf.layers.dense(sampled_z, units=inputs_decoder, activation=lrelu)
        x = tf.layers.dense(x, units=inputs_decoder * 2 + 1, activation=lrelu)
        x = tf.reshape(x, reshaped_dim)
        x = tf.layers.conv2d_transpose(x, filters=64, kernel_size=4, strides=2, padding='same', activation=tf.nn.relu)
        x = tf.nn.dropout(x, keep_prob)
        x = tf.layers.conv2d_transpose(x, filters=64, kernel_size=4, strides=1, padding='same', activation=tf.nn.relu)
        x = tf.nn.dropout(x, keep_prob)
        x = tf.layers.conv2d_transpose(x, filters=64, kernel_size=4, strides=1, padding='same', activation=tf.nn.relu)

        x = tf.contrib.layers.flatten(x)
        x = tf.layers.dense(x, units=seq_len * 1, activation=tf.nn.sigmoid)
        decoder_set = tf.reshape(x, shape=[-1, seq_len, 1])
        return decoder_set
#定义计算loss以及进行优化器优化的一系列tensor
sampled, mn, sd = encoder(X_in, keep_prob)
dec = decoder(sampled, keep_prob)

unreshaped = tf.reshape(dec, [-1, seq_len*1])
img_loss = tf.reduce_sum(tf.squared_difference(unreshaped, Y_flat), 1)
latent_loss = -0.5 * tf.reduce_sum(1.0 + 2.0 * sd - tf.square(mn) - tf.exp(2.0 * sd), 1)
dst_loss=img_loss+latent_loss
loss = tf.reduce_mean(img_loss + latent_loss)
optimizer = tf.train.AdamOptimizer(gConfig['learning_rate']).minimize(loss)
sess = tf.Session()
sess.run(tf.global_variables_initializer())

#开始vae的训练
for i in range(gConfig['vae_steps']):
    batch=dataset
    sess.run(optimizer, feed_dict = {X_in: batch, Y: batch, keep_prob: 0.8})
    if not i % 200:
        ls, d, i_ls, d_ls, mu, sampled_data = sess.run([loss, dec, img_loss, dst_loss, mn, sampled], feed_dict = {X_in: batch, Y: batch, keep_prob: 1.0})

        print(i, ls, np.mean(i_ls), np.mean(d_ls))

#保存训练的encode的结果，就是要进行特征压缩后的特征
sampled_data=pd.DataFrame(sampled_data)
sampled_data.to_csv(gConfig['sampled_path'])


