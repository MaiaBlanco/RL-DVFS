#1 /bin/bash
while true
do 
sudo ./fan_control.py on
sleep 30
sudo ./fan_control.py off
sleep 600
done
