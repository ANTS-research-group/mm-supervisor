import subprocess
import threading
import time
import subprocess
import json
import time
from modules import *
from config import *

def main():

    retries_without_bearer = 0
    retries_without_plmn = 0
    retries_without_ping = 0
    retries_without_address = 0
    plmn_connected = None

    is_modem_regitered = False
    is_modem_connected = False
    is_bearer_activated = False

    log_module = LogModule.get_instance()
    device = DeviceModule.get_instance()

    info_thread = threading.Thread(target=device.get_modem_info)
    info_thread.daemon = True
    info_thread.start()
    
    log = log_module.log
    # waiting for info_thread
    log.debug(f"starting service...")
    time.sleep(GeneralConfig.TIME_DELAY)
    
    while True:

        device = DeviceModule.get_instance()

        while device.modem_index != None and device.modem_info != None:

            # set delay
            time.sleep(GeneralConfig.TIME_DELAY)

            match device.transiction:
                case StateMachineConfig.TRANSICTION_RESET:
                    device.state = StateMachineConfig.STATE_RESET_MODE
                    device.reset_modem(device.modem_index)
                    log.debug(device.state)
                    device.transiction = StateMachineConfig.TRANSICTION_DISCONNECT
                    pass
                case StateMachineConfig.TRANSICTION_DISCONNECT:
                    device.state = StateMachineConfig.STATE_DISCONNECTED_MODE
                    log.debug(device.state)
                    device.transiction = StateMachineConfig.TRANSICTION_CHECK_IS_CONNECTED
                case StateMachineConfig.TRANSICTION_CHECK_IS_CONNECTED:
                    device.state = StateMachineConfig.STATE_CHECK_CONNECTED_MODE
                    log.debug(device.state)
                    device.transiction = StateMachineConfig.TRANSICTION_CONNECT
                case StateMachineConfig.TRANSICTION_CONNECT:


                    if not device.is_regitered:
                        device.is_regitered = device.register_modem(device.modem_index)
                        continue
                    if not device.is_connected:
                        device.is_connected = device.connect_modem(device.modem_index)
                        time.sleep(GeneralConfig.TIME_DELAY_TO_RESET)
                        continue
                    if not device.is_bearer_activated:
                        device.is_bearer_activated = device.is_bearer_active(device.modem_index)
                        continue
                    

                    device.state = StateMachineConfig.STATE_CONNECTED_MODE

                    device.transiction = StateMachineConfig.TRANSICTION_CHECK_HAS_PACKET_SERVICE
                case StateMachineConfig.TRANSICTION_CHECK_HAS_PACKET_SERVICE:
                    
                    # STATE_CHECK_PACKET_SERVICE_MODE
                    if device.modem_info["3gpp"]["packet-service-state"] == "attached":
                        device.state = StateMachineConfig.STATE_CHECK_PACKET_SERVICE_MODE
                        device.transiction = StateMachineConfig.TRANSICTION_SET_DHCP
                    else:
                        device.transiction = StateMachineConfig.TRANSICTION_CONNECT

                case StateMachineConfig.TRANSICTION_SET_DHCP:
                    
                    # check if interface is configured
                    if device.is_interface_configured():
                        log.debug("Interface wwan0 is already configured.")
                        device.transiction = StateMachineConfig.TRANSICTION_SET_INFO
                    else:
                        log.debug("Interface wwan0 is not configured. Reconfiguring.")
                        if device.reconfigure_interface():
                            device.transiction = StateMachineConfig.TRANSICTION_SET_INFO
                        else:
                            device.transiction = StateMachineConfig.TRANSICTION_SET_DHCP

                    if device.transiction == StateMachineConfig.TRANSICTION_SET_INFO:
                        # when interface is configured then check if there is connectivity
                        if not device.check_connectivity():
                            log.error("Connectivity lost. Reconfiguring interface.")
                            device.soft_reset_modem(device.modem_index)
                            result_release = device.release_interface()
                            device.transiction = StateMachineConfig.TRANSICTION_CONNECT
                            continue
                        else:
                            log.debug(f"SET UP GET INFO MODE")
                    else:
                        continue

                    device.state = StateMachineConfig.STATE_CONFIGURE_DHCP_MODE
                    log.debug(device.state)
                    device.transiction = StateMachineConfig.TRANSICTION_SET_INFO
                case StateMachineConfig.TRANSICTION_SET_INFO:
                    device.state = StateMachineConfig.STATE_INFO_MODE
                    
                    # check if it has  packet service again
                    device.transiction = StateMachineConfig.TRANSICTION_CHECK_HAS_PACKET_SERVICE
                case _:
                    pass

            

            
            # bearer_index = device.get_bearer_index(device.modem_index)
            # log.debug(f"Modem index: {device.modem_index}, Active Bearer index: {bearer_index}")

            # # check if there is roaming
            # new_plmn = device.get_plmn_connected(device.modem_index)

            # log.debug(f"new_plmn: {new_plmn}")

            # if new_plmn == None and plmn_connected == None:
            #     retries_without_plmn += 1
            #     if retries_without_plmn >= GeneralConfig.RETRIES_WITHOUT_PLMN:
            #         retries_without_plmn = 0
            #         log.debug(f"Max retries without bearer has been reached.")
            #         log.debug(f"Restarting device and retrying in {GeneralConfig.TIME_DELAY_TO_RESET} seconds.")
            #         # reset_modem(device.modem_index)
            #         time.sleep(GeneralConfig.TIME_DELAY_TO_RESET)
            #         continue
                    
            #     else:
            #         log.debug(f"NEWPLMN and OLDPLMN are None. It was not possible connect to {new_plmn}. Retries: {retries_without_plmn}")
            #         log.debug(f"Trying to connect again with Roaming PLMN {DataNetwork5GConfig.PLMN_ROAMING}...")
            #         continue
            # elif plmn_connected != None and plmn_connected != new_plmn:
            #     log.debug(f"The serving system of the modem has been changed. Old PLMN: {plmn_connected} - New PLMN: {new_plmn}")
            #     log.debug("It's neccesary to reconfigure new bearer")
            #     log.debug("Trying to connect again...")

            #     is_modem_regitered = False
            #     is_modem_connected = False
            #     is_active_bearer = False

            #     continue
            # else:
            #     retries_without_plmn = 0
            
            # if not device.is_interface_configured():
            #     # retries_without_address += 1
            #     # if retries_without_address >= RETRIES_WITHOUT_ADDRESS:
            #     #     log.debug("retries without address has been reached and is_modem_connected is set False")
            #     #     disconnect_modem(device.modem_index, bearer_index)
            #     #     retries_without_address = 0
            #     # else:
            #     log.debug("Interface wwan0 is not configured. Reconfiguring.")
            #     device.reconfigure_interface()
            # else:
            #     #retries_without_address = 0
            #     log.debug("Interface wwan0 is already configured.")

            # if not device.check_connectivity():
            #     # log.debug("Connectivity lost. Reconfiguring interface.")
            #     # reconfigure_interface()
            #     retries_without_ping += 1
            #     if retries_without_ping >= GeneralConfig.RETRIES_WITHOUT_PING:
            #         log.debug("retries without ping has been reached and is_modem_connected is set False")
            #         is_modem_connected = False
            #         retries_without_ping = 0
            #         device.disconnect_modem(device.modem_index)
            #         continue
            #     else:
            #         log.debug("Connectivity lost. Reconfiguring interface.")
            #         device.reconfigure_interface()
            # else:
            #     retries_without_ping = 0


            # # signal_strength = check_signal_strength(device.modem_index)
            # # if signal_strength is None:
            # #     log.debug("Could not retrieve signal strength.")
            # # elif signal_strength < SIGNAL_STRENGTH_TRHRESHOLD:  # Adjust the threshold as needed
            # #     log.debug(f"Low signal strength detected: {signal_strength}%")
            # #     if not check_connectivity():
            # #         log.debug("Connectivity lost. Reconfiguring interface.")
            # #         reconfigure_interface()
            # #     else:
            # #         log.debug("Connectivity is still up despite low signal strength.")
            # # else:
            # #     log.debug(f"Signal strength is sufficient: {signal_strength}%")
            
            
            
            # time.sleep(GeneralConfig.TIME_DELAY)  # Wait for a TIME_DELAY before checking again
        
        log.debug(f"getting modem info")
        time.sleep(GeneralConfig.TIME_DELAY)  # Wait for a TIME_DELAY before checking again



if __name__ == "__main__":
    main()
