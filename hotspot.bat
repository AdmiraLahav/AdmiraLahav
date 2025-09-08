@echo off
:: Hotspot setup
set ssid=MyHotspot
set key=MyPassword123

echo Creating hotspot "%ssid%" ...
netsh wlan set hostednetwork mode=allow ssid=%ssid% key=%key%

echo Starting hotspot...
netsh wlan start hostednetwork

echo.
echo Hotspot "%ssid%" is running with password "%key%"
pause