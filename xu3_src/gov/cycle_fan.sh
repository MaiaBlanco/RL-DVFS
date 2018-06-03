#1 /bin/bash
while true
do 
sudo ./fan_control.py on
sleep 5
sudo ./fan_control.py off
sleep 600
done
