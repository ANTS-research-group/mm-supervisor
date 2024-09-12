
import logging
import os
import sys
import traceback
from config import LoggingConfig
from logging.handlers import TimedRotatingFileHandler

class LogModule:

    
    

    __unique_instance = object()

    def __init__(self, instance):

        try:
            assert(instance == LogModule.__unique_instance)
        except AssertionError as e:
            
            self.log.error("LogModule object must be created using LogModule.get_instance()")
            traceback.print_stack()
            sys.exit(-1)

        self.create_structure()

        log_dir_path = LoggingConfig.LOG_DIR_PATH
        log_file_path = LoggingConfig.LOG_SYSTEM_FILE_PATH
        log_path = f"{log_dir_path}{log_file_path}"
        log_file_handler_format = logging.Formatter('%(asctime)s - %(levelname)s - [line %(lineno)d in %(filename)s] %(message)s ')

        log_file_handler = logging.FileHandler(filename=log_path, encoding='utf-8')
        log_file_handler.setLevel(LoggingConfig.LOG_DEBUG_LEVEL_FILE)
        log_file_handler.setFormatter(log_file_handler_format)
        log_file_handler.mode = 'w'

        consoleHandler = logging.StreamHandler(sys.stdout)
        consoleHandler.setLevel(LoggingConfig.LOG_DEBUG_LEVEL_CONSOLE)
        consoleHandler.setFormatter(log_file_handler_format)

        rotatingHandler = TimedRotatingFileHandler(filename=log_path, when="d", interval=1, backupCount=7, encoding='utf-8')
        rotatingHandler.setLevel(LoggingConfig.LOG_DEBUG_LEVEL_FILE)
        rotatingHandler.setFormatter(log_file_handler_format)
        rotatingHandler.mode = 'w'

        self.log = logging.getLogger("clients")
        self.log.setLevel(LoggingConfig.LOG_MAX_DEBUG_LEVEL)
        self.log.addHandler(consoleHandler)
        self.log.addHandler(rotatingHandler)

        
        

    @classmethod
    def get_instance(cls):
        if isinstance(cls.__unique_instance, LogModule):
            #config.log.debug("instance of LogModule created before")
            return cls.__unique_instance
        try:
            cls.log.debug("LogModule instance was created successfully")
        except Exception as e:
            # print(e)
            pass

        cls.__unique_instance = LogModule(cls.__unique_instance)
        return cls.__unique_instance

    def create_structure(self):

        log_dir_path = LoggingConfig.LOG_DIR_PATH
        log_system_file_path = f"{log_dir_path}{LoggingConfig.LOG_SYSTEM_FILE_PATH}"
        log_stats_file_path_json = f"{log_dir_path}{LoggingConfig.LOG_STATS_FILE_PATH_JSON}"

        # create log directory if not exists
        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path, exist_ok=True)

        # create log file if not exists
        def create_file_if_not_exists(file_path):
            if not os.path.exists(file_path):
                
                parent_dir = os.path.dirname(file_path)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                with open(file_path, 'w') as archivo:
                    archivo.write("")

        
        create_file_if_not_exists(log_system_file_path)
        create_file_if_not_exists(log_stats_file_path_json)
        