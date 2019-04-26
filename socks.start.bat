@ECHO OFF
ECHO Starting Socks Server...
hide E:\workspace\networktunnel\venv\Scripts\twistd.exe -y E:\workspace\networktunnel\local.tac
hide E:\workspace\networktunnel\ss_win_temp\ss_privoxy.exe -c E:\workspace\networktunnel\ss_win_temp\privoxy.conf
