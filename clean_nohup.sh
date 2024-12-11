ps aux | grep multi | awk '{print $2}' | xargs -ti kill -9 {}
