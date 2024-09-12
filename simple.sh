#mmcli -m 2 -d
#mmcli -m 2 -e
mmcli -m 2 --3gpp-register-in-operator="00101"
mmcli -m 2 --simple-connect="apn=internet,ip-type=ipv4" --create-bearer="operator-id=00101" -J
sudo udhcpc -R -i wwan0
