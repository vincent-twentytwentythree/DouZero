#python train.py --gpu_devices 0,1,2,3,4,5,6,7 --actor_device_cpu --num_actors 1 --training_device 3 --save_interval 20 --load_model --training_mode second_hand --exp_epsilon -1.0 --debug
python train.py --gpu_devices 0,1,2,3,4,5,6,7 --actor_device_cpu --num_actors 1 --training_device 3 --save_interval 20 --load_model --training_mode landlord --exp_epsilon -1.0 # --debug
