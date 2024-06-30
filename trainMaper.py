import tensorflow as tf
import os
import numpy as np
import matplotlib.pyplot as plt
import models as mod
import helper
import losses
import config

id = 0 
config.config_gpu(id)

model_name = 'Mapper'

batch_size = 128
epochs     = 300
save_every = 20
sigma      = 17

noise_type='Rician'
tes = np.array([0.93, 2.27, 3.61, 4.95, 6.29, 7.63, 8.97, 10.4, 11.8, 13.2, 14.6, 16.0])
data_dir = os.path.join('data','liver',noise_type)
# wImg    = np.load(os.path.join(data_dir,'wImg_1.0.npy')).astype(np.float32)
wImgN   = np.load(os.path.join(data_dir,'wImgN'+str(sigma)+'_1.0.npy')).astype(np.float32)
# wImg    = np.load(os.path.join(data_dir,'wImg_2.5.npy')).astype(np.float32)
# wImgN   = np.load(os.path.join(data_dir,'wImgN'+str(sigma)+'_2.5.npy')).astype(np.float32)
# wImg    = np.load(os.path.join(data_dir,'wImg.npy')).astype(np.float32)
# wImgN   = np.load(os.path.join(data_dir,'wImgDn'+str(sigma)+'.npy')).astype(np.float32)

pImg    = np.load(os.path.join(data_dir,'pImg_1.0.npy')).astype(np.float32)

maskBody= np.load(os.path.join(data_dir,'maskBody.npy')).astype(np.float32)
maskBodyw= np.repeat(maskBody,6,axis=-1)

# wImg  = wImg*maskBodyw
wImgN  = wImgN*maskBodyw
pImg  = pImg*maskBody

# wPatch  = helper.makePatch(wImg[0:100],patch_size=32,stride=8,rescale=True,aug_times=4)
wPatchN = helper.makePatch(wImgN[0:100],patch_size=32,stride=8,rescale=True,aug_times=4)
pPatch = helper.makePatch(pImg[0:100],patch_size=32,stride=8,rescale=True,aug_times=4)
# wPatchN = helper.addNoiseMix(wPatch,sigma_low=1.0,sigma_high=19,noise_type='Rician')
# wPatchN = np.load(os.path.join(data_dir,'wPatchNmixDn.npy'))

# mPatch  = helper.makePatch(maskBody[0:100],patch_size=32,stride=8,rescale=True,aug_times=4)
# wPatchN = wPatchN*mPatch
# np.save(os.path.join(data_dir,'wPatchNmix'),wPatchN)
# wPatchN = np.load(os.path.join(data_dir,'wPatchNmix.npy'))

index   = np.random.permutation(wPatchN.shape[0])
# wPatch  = wPatch[index]
wPatchN = wPatchN[index]
pPatch = pPatch[index]

plt.figure(figsize=(15,10))
iTrn = 2400
plt.subplot(2,3,1),plt.axis('off')
plt.imshow(wPatchN[iTrn,:,:,0],  cmap='gray',interpolation='none',vmin=0,vmax=400),plt.title('TE0'),plt.colorbar(fraction=0.022)
plt.subplot(2,3,2),plt.axis('off')
plt.imshow(wPatchN[iTrn,:,:,1],  cmap='gray',interpolation='none',vmin=0,vmax=400),plt.title('TE1'),plt.colorbar(fraction=0.022)
plt.subplot(2,3,3),plt.axis('off')
plt.imshow(wPatchN[iTrn,:,:,2],  cmap='gray',interpolation='none',vmin=0,vmax=400),plt.title('TE2'),plt.colorbar(fraction=0.022)
plt.subplot(2,3,4),plt.axis('off')
plt.imshow(pPatch[iTrn,:,:,0], cmap='jet',interpolation='none',vmin=0,vmax=400),plt.title('s0'),plt.colorbar(fraction=0.022)
plt.subplot(2,3,5),plt.axis('off')
plt.imshow(pPatch[iTrn,:,:,1], cmap='jet',interpolation='none',vmin=0),plt.title('r2'),plt.colorbar(fraction=0.022)
plt.subplot(2,3,6),plt.axis('off')
plt.imshow(pPatch[iTrn,:,:,1], cmap='jet',interpolation='none',vmin=0),plt.title('r2'),plt.colorbar(fraction=0.022)
plt.savefig(os.path.join('figure','patchTrn'+str(iTrn)))

model_dir = os.path.join('model',model_name+'_'+'sigma'+str(sigma))
if not os.path.exists(model_dir): os.mkdir(model_dir)

img_channels  = 12
# model_denoise = mod.SeparableCNN(depth=8,depth_multi=10,filters=40,image_channels=img_channels,dilation=1)
model_mapping = mod.UNetH(image_channels=img_channels)
# model = mod.UNetDouble(image_channels=img_channels)

inpts = tf.keras.Input(shape=(None,None,img_channels))
# outpts_denoising = model_denoise(inpts)
# outpts_mapping   = model_mapping(outpts_denoising)
outpts_mapping   = model_mapping(inpts)

# model = tf.keras.Model(inputs=inpts,outputs=[outpts_denoising,outpts_mapping])
# model = tf.keras.Model(inputs=inpts,outputs=outpts_denoising)
model = tf.keras.Model(inputs=inpts,outputs=outpts_mapping)

# file_writer = tf.summary.create_file_writer(model_dir)
# file_writer.set_as_default()
# loss3 = losses.loss_model_exp_image(outpts_denoising,outpts_mapping)
# model.add_loss(loss3)

model.summary()

# load the last model parameters
initial_epoch = helper.findLastCheckpoint(save_dir=model_dir)
if initial_epoch > 0:
    print('Resuming by loading epoch %03d'%initial_epoch)
    model = tf.keras.models.load_model(os.path.join(model_dir,'model_%03d.h5'%initial_epoch), compile=False)

# compile the model
model.compile(optimizer=tf.keras.optimizers.Adam(),
              loss=[losses.sum_squared_error],
              )

checkpointer = tf.keras.callbacks.ModelCheckpoint(os.path.join(model_dir,'model_{epoch:03d}.h5'), verbose=1, save_weights_only=False, period=save_every)
csv_logger   = tf.keras.callbacks.CSVLogger(os.path.join(model_dir,'log.csv'), append=True, separator=',')
lr_scheduler = tf.keras.callbacks.LearningRateScheduler(helper.lr_schedule2)
tensorboard  = tf.keras.callbacks.TensorBoard(log_dir=model_dir, histogram_freq=1)

# import callbacks
model.fit(  x=wPatchN,
            # y=[wPatch],
            y=pPatch,
            epochs=epochs,
            initial_epoch=initial_epoch,
            batch_size=batch_size,
            validation_split = 0.2,
            shuffle=True,
            callbacks=[checkpointer,csv_logger,lr_scheduler,tensorboard],
            )