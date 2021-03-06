
import re, string, pdb, os.path
from nested_dict import flatten, unflatten, filter_flatten_dict
from Logger import Logger


def update_leaf(initial_dict, update_dict):
    """Smart update of dictionaries, by leaf.

    TODO Not implemented yet. Returning simple dict update.
    IDEA: Make tuple dict where tuple is made of keys and value is the last node.


    It will update recursivlely, only when the leaf is found.
    For example:
    a = {'a':1, 'b':{'c':2, 'd':'3'}}
    b = {'a':2, 'b':{'c':3, 'e':'3'}}
    c = update_leafs(a,b)
    c = {'a':2, 'b':{'c':3,'e':'3','d':'3'}}
    """
    import nested_dict as nd
    nd_initial_dict = nd.nested_dict(initial_dict)
    nd_update_dict = nd.nested_dict(update_dict)
    nd_initial_dict.update(nd_update_dict)
    return nd_initial_dict.to_dict()

class UniversalConfigParser(object):
    """
    Wraper for XML, YAML, JSON, INI which can return dictionary.

    """
    #from lib.util.Logger import *
    supported_cfg_types = ['yaml','xml','json','ini']
    def __init__(self, cfg_type=None, file_list = None):
        self.my_logger = Logger()
        self.log = self.my_logger.getLogger(self.__class__.__name__, level = 10)
        self.DEBUG = self.my_logger.is_debug()

	self.cfg_type = self.set_cfg_type(cfg_type)
	self.file_list = self.set_files(file_list)
	self.cfg_dict = {}



    def _get_cfg_type(self,file_name):

	if self.cfg_type == None :
	    self.log.debug('The type of CFG file is being be figured out from file extension.')
	    import os.path
	    #import re
	    #cfg_type = re.sub(r".",'',os.path.splitext(file_name)[-1]).lower()
	    cfg_type = os.path.splitext(file_name)[1].replace('.','')

	assert cfg_type in self.supported_cfg_types,("Cannont figure out the "
             "configuration file type. Supported CFG types are only {0}").format(self.supported_cfg_types)
	return cfg_type

    def set_cfg_type(self,cfg_type):
	self.log.debug('Checking the validity of CFG type.')

	if cfg_type == None: return None
	try: cfg_type  = cfg_type.lower()
	except AttributeError:
	    raise AttributeError, "You have to provide a string as CFG type."
	assert cfg_type in self.supported_cfg_types,("CFG type not supported."
            "Supported CFG types are only {0}").format(self.supported_cfg_types)
	return cfg_type

    def setLogLevel(self,level): self.log.setLevel(level)

    def set_files(self, file_list):
	"""
	Check if list is list or a CSV string. In case of string, create a list.
	"""
	if file_list==None: return []
	import types
	isString = isinstance(file_list, types.StringTypes)
	isList   = isinstance(file_list, list)
	assert isString or isList,('You should provide a list of files as '
                                    'list or as CVS string!')
	if isList: return file_list
	if isString :
	  import re
	  #remove all whitespaces
	  file_list_converted = re.sub(r'\s', '', file_list).split(',')
	  return file_list_converted

    def item(self, item_name):
	"""Get one item from cfg dictionary.

	If the item is nested, then use "." to set the path to the item.
	Check the implementation in XmlDictConverter.py
	"""
	self.log.info('Not implemented yet... Sorry!')
	pass

    def get_dict(self, file_list=None, cfg_type=None):
	"""
	Returns the full configuration in the form of dictionary.
	"""
	if file_list:
            self.file_list = self.set_files(file_list)
        self.cfg_dict = {}
        if cfg_type:
            self.cfg_type = self.set_cfg_type(cfg_type)

	self.log.debug('Getting dictionary from config files: %s', str(self.file_list))
	for cfg_file in self.file_list:
	    """
	    We want to append dictionaries from all the config files.
	    """
	    self.this_cfg_dir = os.path.dirname(os.path.abspath(cfg_file))
	    #os.environ['THIS_CFG_DIR'] =  str(self.this_cfg_dir)

	    if self.cfg_type == None: self.cfg_type = self._get_cfg_type(cfg_file)
	    self.log.debug('Updating dictionary from config file in the order provided: %s',str(cfg_file) )
	    if self.cfg_type.lower() in ['yaml', "yml"]: self._get_dict_yaml(cfg_file)
	    elif self.cfg_type.lower() == 'xml': self._get_dict_xml(cfg_file)
	    elif self.cfg_type.lower() == 'json': self._get_dict_json(cfg_file)
	    elif self.cfg_type.lower() == 'ini': self._get_dict_ini(cfg_file)


        #check for interpreter_keywors
        #loop on dict and update values with values from another cfg.
        #used to input values from other cfg files.
        self._interpret_keywords_and_update(self.cfg_dict)

	return self.cfg_dict

    def get_cfg_dirname(self):
        """
        Get abspath of directory where current config lives.
        """
        return self.this_cfg_dir


    def _interpret_keywords_and_update(self, this_dict):
        """
        - check for interpreter_keywords
        - loop on dict and update values with values from another cfg.
        - used to input values from other cfg files.
        """
        keywords = ['INSERT']
        self.log.debug('Keywords: {0}'.format(keywords))

        def recursive_parse(obj):
            new_obj = obj
            #self.log.debug('recursive_parse: {0} type={1}'.format(obj, type(obj)))
            #self.log.debug('recursive_parse: {0} '.format(obj))

            if isinstance(obj, dict):
                for key in new_obj:
                    #we iterate further only if it's a list or a dict
                    #self.log.debug('recursive_parse loop: {0} type={1}'.format(k,type(obj[k])))
                    recursive_parse(obj[key])

                    ##now do the interatation
                    if isinstance(obj[key], str):
                        all_matches = re.findall("INSERT\((.+?)\)",str(obj[key]))
                        #print 'all_matches_dict', all_matches
                        if len(all_matches)>0:
                            self.log.debug('Parsing with INSERT: {0}'.format(obj[key]))
                            obj[key] = INSERT(obj[key])
                            #pdb.set_trace()

            elif isinstance(obj, list):
                for idx, item in list(enumerate(new_obj)):
                    #we iterate further only if it's a list or a dict
                    #self.log.debug('recursive_parse loop: {0} type={1}'.format(k,type(obj[k])))
                    #if isinstance(obj[key], dict):
                    recursive_parse(item)

                    ##now do the interatation
                    if isinstance(item, str):
                        all_matches = re.findall(r"INSERT\((.+?)\)",str(item))
                        #print 'all_matches_list', all_matches
                        if len(all_matches)>0:
                            self.log.debug('Parsing with INSERT: {0}'.format(item))
                            obj[idx] = INSERT(obj[idx])


        def INSERT(input_line):
            """
            Receives the line and parses like:
            'INSERT(path_to_file_with_yields.yaml:2e2mu:ggH)'
            - reads config from path_to_file_with_yields.yaml
            - gets value for full_config['2e2mu']['ggH']
            """
            pattern = "INSERT\((.+?)\)"
            p = re.compile(r'''
                    INSERT     #look for INSERT
                    \(         #match opening (
                    [^\(\)]*?  #match anything but ( or )
                    \)         #match closing )
                    ''', re.VERBOSE)
            #tokens = p.split(input_line)
            #matching_tokens = p.findall(input_line)
            tokens = re.split(pattern, input_line)
            matching_tokens = re.findall(pattern, input_line)


            #raise error if using multiple enclosed INSERT commands INSERT(INSERT()...)
            if p.search(p.sub('XXX',input_line)):
                raise RuntimeError, ('Multiple-level INSERT commands are not allowed. '
                                     'Check your configuration files.')

            self.log.debug('tokens: {0}\nmatching_tokens: {1}'.format(tokens, matching_tokens))

            new_input_line=''
            enforce_string = True


            if len(matching_tokens)==1:
                striped_line = input_line.lstrip('INSERT(').rstrip(')')
                if matching_tokens[0] == striped_line:
                    #we can insert the dict or whatever object
                    enforce_string = False

            for tok in tokens:
                if tok in matching_tokens:
                    #now read from other config
                    inputs = tok.split(':')
                    filename = inputs[0]
                    keys = inputs[1:]
                    self.log.debug('filename = {0} keys={1}'.format(filename, keys))
                    if filename!='THIS_CONFIG':
                        self.log.debug('filename = {0} keys={1} this_cfg_dir={2}'
                            .format(filename, keys, self.this_cfg_dir))
                        filename = os.path.join(self.this_cfg_dir,
                                                os.path.dirname(filename),
                                                os.path.basename(filename))
                        another_cfg_reader = UniversalConfigParser(cfg_type="YAML",
                                                                   file_list = filename)
                        full_config = another_cfg_reader.get_dict()
                        #TODO check that youare notrreading the same file which is already read not to blow up the memory.
                        #print full_config
                        if len(keys)>0:
                            #check if there are wildcards used
                            #use_fnmatch = any(c in '*?[],' for c in string.join(keys))
                            #p = re.compile(r'[\*\?\[\]\,]')  #wildcards possible '*?[],'
                            use_fnmatch = bool(re.search(r'[\*\?\[\]\,]', string.join(keys)))

                            if use_fnmatch:
                                partial_config_flat = filter_flatten_dict(flatten(full_config),keys)
                                partial_config = unflatten(partial_config_flat).to_dict()

                                #if len(new_dict.keys)==1 return the value
                                if len(partial_config_flat.keys())==1:
                                    partial_config = partial_config_flat[partial_config_flat.keys()[0]]

                            else:
                                partial_config = full_config
                                for item in keys:
                                    #in this way we get the last item
                                    partial_config = partial_config[item]

                            if not enforce_string:
                                return partial_config
                            else:
                                new_input_line+=str(partial_config)  #basically inserts value
                        else:
                            return full_config



                    else:
                        raise RuntimeError, 'THIS_CONFIG is not yet implemented keyword!'


                else:
                    new_input_line+=tok
            #print new_input_line
            if enforce_string:
                return new_input_line

        recursive_parse(this_dict)


        if self.DEBUG:
            self.log.debug('Updated dictionary (after reparsing) keywords: ')
            print this_dict
        return this_dict


    def _get_dict_yaml(self,file_name):
        self.log.debug('Reading yaml configuration and updating dictionary.')
        import yaml
        with open(file_name,'r') as fd:
            self.cfg_dict.update(yaml.load(fd))


    def _get_dict_xml(self,file_name):
        import lib.util.XmlDictConverter as xmlc
        self.cfg_dict.update(xmlc.ConvertXmlToDict(file_name))


    def _get_dict_json(self,file_name):
        #import json
        #with open(file_name) as fd:
            #self.cfg_dict.update(json.load(fd))
        import lib.util.ConfigHelpers as ch
        self.cfg_dict.update(ch.parse_json(file_name))



    def _get_dict_ini(self,file_name):
        import lib.util.ConfigHelpers as ch
        ini = ch.ConfigParserWrapper()
        with open(file_name,'r') as fd:
            self.cfg_dict.update(ini.load(fd))

    def dump_to_json(self,dump_file_name, new_dict):
       import json
       if os.path.dirname(dump_file_name) and not os.path.exists(os.path.dirname(dump_file_name)):
            os.makedirs(os.path.dirname(dump_file_name))

       with open(dump_file_name, "w") as json_file:
            json_file.write(json.dumps(new_dict, indent=4))
            self.log.info('Written json file: {0}'.format(dump_file_name))


    def dump_to_yaml(self,dump_file_name, new_dict):
        import yaml
        if os.path.dirname(dump_file_name) and not os.path.exists(os.path.dirname(dump_file_name)):
                os.makedirs(os.path.dirname(dump_file_name))
        with open(dump_file_name, 'w') as yaml_file:
            yaml_file.write( yaml.dump(new_dict, default_flow_style=False))
            self.log.info('Written yaml file: {0}'.format(dump_file_name))

