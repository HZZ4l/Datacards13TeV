
import logging


BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

#The background is set with 40 plus the number of the color, and the foreground with 30

#These are the sequences need to get colored ouput
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

def formatter_message(message, use_color = True):
    if use_color:
        message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message

COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
}

class ColoredFormatter(logging.Formatter):
    def __init__(self, msg, use_color = True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)



class Logger(object):
    COMPANY_LOGGER = 'My.Python.Logger'
    CONSL_LEVEL_RANGE = range(0, 51)
    LOG_FILE = 'last.log'
    #FORMAT_STR = '%(asctime)s %(levelname)s %(message)s'
    #FORMAT_STR = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    FORMAT_STR = '------- %(name)-12s : %(levelname)-8s :  %(message)s'
    FORMAT = "------- $BOLD%(name)-12s$RESET : %(levelname)-8s : %(message)s ------- (in file $BOLD%(filename)s$RESET : %(lineno)d)"
    COLOR_FORMAT = formatter_message(FORMAT, True)
    
    def setVerbose(self, logger, verbose=0):
        """Set level of verbosity with integer:
           <1  = very quiet
           >4  = a lot of bla bla
        """
        if verbose<=0 : verbose = 0
        if verbose>5  : verbose = 5
        my_level = 51 - int(verbose*10)
        self.level = my_level
        logger.setLevel(my_level)
        
      
    def getLevel(self, level):
        if level is None: return
        try: level = int(level)
        except: pass
        if level not in self.CONSL_LEVEL_RANGE:
            #args.console_log = None
            print 'warning: console log level ', level, ' not in range 1..50.'
            return
        return level
        
    def is_debug(self):
        print 'info: you are running in mode DEBUG =', (self.logger.getEffectiveLevel()<20)
        return (self.logger.getEffectiveLevel()<20)
        
    def setLevel(self, level):
        if level is None: return
        try: level = int(level)
        except: pass
        if level > 50 : level = 50
        elif level <0 : level = 0
        if level not in self.CONSL_LEVEL_RANGE:
            #args.console_log = None
            print 'warning: console log level ', level, ' not in range 1..50.'
            return
        self.logger.setLevel(level)

    def getLogger(self, logger_name=COMPANY_LOGGER, level=logging.DEBUG, log_file = None):
        ## Create logger
        #print logger_name, level,log_file
        self.logger = logging.getLogger(logger_name)
        import os
        if os.getenv('PYTHON_LOGGER_VERBOSITY'):
            #print "PYTHON_LOGGER_VERBOSITY is set to :", int(os.getenv('PYTHON_LOGGER_VERBOSITY'))
            self.setVerbose(self.logger, int(os.getenv('PYTHON_LOGGER_VERBOSITY')) )
            
        else:
            self.level = self.getLevel(level)
            self.logger.setLevel(level)
        self.formatter = ColoredFormatter(self.COLOR_FORMAT)
        
        #check if there is already a handler for this logger to avoid mltiplication of log lines. 
        if self.logger.handlers != []: 
            return self.logger
        
        
        # Add FileHandler
        if log_file is not None:
            self.fh = logging.FileHandler(self.LOG_FILE)
            self.fh.name = 'File Logger'
            #fh.level = logging.WARNING
            self.fh.formatter = self.formatter
            self.logger.addHandler(self.fh)
        if self.level is not None:
            self.ch = logging.StreamHandler()
            self.ch.name = 'Console Logger'
            #ch.level = level
            self.ch.formatter = self.formatter
            self.logger.addHandler(self.ch)
            
        return self.logger

        
        