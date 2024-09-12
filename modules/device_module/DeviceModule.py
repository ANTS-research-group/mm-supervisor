import json
import subprocess
import sys
import time
import traceback
from modules.log_module import LogModule
from config import *

class DeviceModule:

    
    __unique_instance = object()
    

    def __init__(self, instance):

        try:
            assert(instance == DeviceModule.__unique_instance)
        except AssertionError as e:
            
            self.log.error("Device object must be created using Device.get_instance()")
            traceback.print_stack()
            sys.exit(-1)

        self.modem_index = None
        self.modem_info = None
        log_module = LogModule.get_instance()
        self.log = log_module.log

        self.is_regitered = None
        self.is_connected = None
        self.is_bearer_activated = None

        self.state = StateMachineConfig.STATE_DISCONNECTED_MODE
        self.transiction = StateMachineConfig.TRANSICTION_CONNECT

        

    @classmethod
    def get_instance(cls):
        if isinstance(cls.__unique_instance, DeviceModule):
            #config.log.debug("instance of Device created before")
            return cls.__unique_instance
        try:
            cls.log.debug("LogModule instance was created successfully")
        except Exception as e:
            # log.debug(e)
            pass

        cls.__unique_instance = DeviceModule(cls.__unique_instance)
        return cls.__unique_instance


    def run_mmcli_command(self, command):
        result = subprocess.run(command, capture_output=True, text=True)

        if result.stderr:
            return None
        
        return json.loads(result.stdout)

    def get_modem_index(self):
        result = self.run_mmcli_command(['mmcli', '-L', '-J'])
        result = result.get("modem-list", [])

        for modem in result:
            self.modem_index = modem.split('/')[-1]
            return self.modem_index
        return None
        
    def get_bearer_index(self, modem_index):

        result = self.run_mmcli_command(['mmcli', '-m', modem_index, '-J'])

        result = result.get('modem', [])
        if result == None:
            return None
        result = result.get('generic', [])
        if result == None:
            return None
        result = result.get('bearers', [])
        if result == None:
            return None

        for bearer in result:
            return bearer.split('/')[-1]
            
        return None

    def is_bearer_connected(self, bearer_index):
        bearer_result = self.run_mmcli_command(['mmcli', '-b', bearer_index, '-J'])
        bearer_result = bearer_result.get("bearer", [])
        
        if bearer_result['status']['connected'] == 'yes':
            return True
        return False
        
    def check_signal_strength(self, modem_index):
        result = self.run_mmcli_command(['mmcli', '-m', modem_index, '-J'])
        result = result.get('modem', [])
        if result == None:
            return None
        result = result.get('generic', [])
        if result == None:
            return None
        if 'signal-quality' in result:
            quality = int(result['signal-quality']['value'])
            return quality
        return None

    def check_connectivity(self):

        result = subprocess.run(['ping', '-I', 'wwan0', '-W', '1', '-c', '1', '8.8.8.8'], capture_output=True)
        return result.returncode == 0


    def get_plmn_connected(self, modem_index):
        result = self.run_mmcli_command(['mmcli', '-m', modem_index, '-J'])

        result = result.get('modem', [])
        if result == None:
            return None
        result = result.get('3gpp', [])
        if result == None:
            return None
        if result['packet-service-state'] == 'attached':
            return result['operator-code']
        
        return None

    def is_interface_configured(self):
        result = subprocess.run(['ip', 'addr', 'show', 'wwan0'], capture_output=True, text=True)
        return 'inet ' in result.stdout

    def reconfigure_interface(self):
        result = subprocess.run(['sudo', 'udhcpc', '-n', '-q', '-f', '-i', 'wwan0', '-t', '5', '-T', '1'])
        self.log.debug(result)

        if self.is_interface_configured():
            return True
        
        return None

    def release_interface(self):
        try:

            result = subprocess.run(['sudo', 'ip', 'addr', 'flush', 'dev', 'wwan0'], capture_output=True, text=True)
            if result.returncode == 0:
                return True
            else:
                return False
        except subprocess.CalledProcessError as e:
            self.log.error(f"IP wasn't released: {e}")
            return False
    
    def soft_reset_modem(self, modem_index):

        global disconnecting_modem
        disconnecting_modem = True

        result_output = subprocess.run(['mmcli', '-m', modem_index, '-d'], capture_output=True, text=True)
        result = False
        if "successfully disabled the modem" in result_output.stdout:
            result_output = subprocess.run(['mmcli', '-m', modem_index, '-e'], capture_output=True, text=True)
            if "successfully enabled the modem" in result_output.stdout:
                self.is_connected = False
                self.is_regitered = False
                self.is_bearer_activated = False
                result = True
            else: result = False
        
        disconnecting_modem = False

        return result

    def connect_modem(self, modem_index):

        result = subprocess.run(
            [
                'mmcli', '-m', modem_index,
                f'--simple-connect=apn={DataNetwork5GConfig.APN},ip-type={DataNetwork5GConfig.IP_TYPE}',
                f'--create-bearer=operator-id={DataNetwork5GConfig.PLMN_HOME}'
            ], 
            capture_output=True,
            text=True
            )

        if "successfully connected the modem" in result.stdout:
            return True
        else:
            self.log.debug(f"device wasn't connected: {result.stderr}")
            return False

    def register_modem(self, modem_index, plmn=DataNetwork5GConfig.PLMN_HOME):
        
        registered = None
        for plmn in DataNetwork5GConfig.PLMN_LIST_ALLOWED:
            result = subprocess.run(['mmcli', '-m', modem_index, f'--3gpp-register-in-operator={plmn}', '-J'], capture_output=True, text=True)
            if "successfully registered the modem" in result.stdout:
                
                registered = True
            elif "Cannot register modem: modem is connected" in result.stderr:
                registered = True
            else:
                self.log.debug(f"device wasn't registered: {result.stderr}")
                registered = False
            if registered:
                return True
        return registered
    def get_modem_info(self):

        while True:

            self.modem_index = self.get_modem_index()

            if self.modem_index is None:
                self.modem_info = None
                self.log.debug(f"No modem found. Retrying in {GeneralConfig.TIME_DELAY_TO_RESET} seconds.")
                time.sleep(GeneralConfig.TIME_DELAY_TO_RESET)
                continue

            result = self.run_mmcli_command(['mmcli', '-J', '-m', self.modem_index])
            result = result.get('modem', [])
            
            if result:
                self.modem_info = result
            else:
                self.modem_info = None

            time.sleep(GeneralConfig.TIME_DELAY)

    def reset_modem(self, modem_index):
        subprocess.run(['mmcli', '-m', modem_index, '--reset', '-J'])

    def is_bearer_active(self, modem_index):

        bearer_index = self.get_bearer_index(modem_index)

        if bearer_index is None: return None

        is_b_connected = self.is_bearer_connected(bearer_index)
        
        return is_b_connected