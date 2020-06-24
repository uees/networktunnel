@ECHO OFF
echo Stopping Socks5 proxy Server...
taskkill /f /IM twistd.exe >> nul
taskkill /f /IM twistd.exe >> nul
taskkill /f /IM twistd.exe >> nul
taskkill /f /IM twistd.exe >> nul
echo Stopping http proxy Server...
taskkill /f /IM ss_privoxy.exe >> nul
taskkill /f /IM ss_privoxy.exe >> nul
taskkill /f /IM ss_privoxy.exe >> nul
taskkill /f /IM ss_privoxy.exe >> nul
echo Stopping dns2socks Server...
taskkill /f /IM dns2socks.exe >> nul
taskkill /f /IM dns2socks.exe >> nul
taskkill /f /IM dns2socks.exe >> nul
taskkill /f /IM dns2socks.exe >> nul
