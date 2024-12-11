
ps aux | grep train.py | awk '{print $2}' | xargs -ti kill -9 {}
ps aux | grep multi | awk '{print $2}' | xargs -ti kill -9 {}
