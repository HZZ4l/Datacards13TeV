#!/usr/bin/env python

#-------------------------------------------------------------------------------
# Author:   Roko Plestina (IHEP-CAS), 2015
# Purpose:
#    - building "combine" datacards from dictionaries in config files
#    - testing the inputs (in future, plotting)
#    - making a webpage for easier testing.
#-------------------------------------------------------------------------------

import sys,os,re, optparse, pprint, textwrap, string

from ROOT import RooFit, RooWorkspace, RooArgSet, RooArgList
from ROOT import RooDataHist, RooHistPdf, gSystem
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             os.pardir, os.pardir)))
from lib.util.Logger import Logger
from lib.util.UniversalConfigParser import UniversalConfigParser
from lib.RootHelpers.RootHelperBase import RootHelperBase
from lib.RooFit.ToyDataSetManager import ToyDataSetManager
from lib.util.MiscTools import flatten_list
import lib.util.nested_dict as nd

class LegoCards(object):
    """
    Class for building datacards, both textual and workspace part

    EXAMPLE_____________________________________________________________________
    #*** HEADER ***
    imax 1 number of bins
    jmax 3 number of processes minus 1
    kmax 1 number of nuisance parameters
    ----------------------------------------------------------------------------
    shapes *    ch1  hzz4l_2e2muS_8TeV_SM_125_mass4l_v3.Databin0.root w:$PROCESS
    ----------------------------------------------------------------------------
    bin          ch1
    observation  8.0
    #***PER-PROCESS INFORMATION ***
    ----------------------------------------------------------------------------
    bin         ch1               ch1               ch1               ch1
    process     trueH2e2muBin0_8  bkg_zjets_8       bkg_ggzz_8        bkg_qqzz_8
    process     0                 1                 2                 3
    rate        1.0000            1.0526            0.3174            5.7443
    ----------------------------------------------------------------------------
    CMS_eff_e   lnN           1.046             -                 1.046

    EXAMPLE_____________________________________________________________________

    """

    #___________________________________________________________________________
    def __init__(self, datacard_input, datacard_name = None ):
        self.my_logger = Logger()
        self.log = self.my_logger.getLogger(self.__class__.__name__, 10)
        self.DEBUG = self.my_logger.is_debug()
        self.pp = pprint.PrettyPrinter(indent=4)

        #

        self.datacard_name = datacard_name
        self.d_input = datacard_input
        if self.DEBUG:
            self.pp.pprint(self.d_input)

        self.cfg_absdir = None
        self.log.debug('Datacard: {0} Datacard input: {1}'.format(self.datacard_name,
                                                                  self.d_input))

        #self.not_a_process = ['observation','functions_and_definitions', 'setup']
        self.not_a_process = self.d_input['setup']['reserved_sections']
        self.lumi_scaling = 1.0

        #process lists
        self.signal_process_list = self._get_processes('signal')
        self.bkg_process_list = self._get_processes('background')
        self.process_list = self.signal_process_list+self.bkg_process_list

        self.log.debug('Processes: {0}'.format(self.process_list))

        #self.n_systematics, self.systematics_lines = self._get_systematics_lines()
        self.card_header='' #set of information lines os a header of the card.

    ###########################################################################
    #              _     _ _                       _   _               _      #
    #  _ __  _   _| |__ | (_) ___   _ __ ___   ___| |_| |__   ___   __| |___  #
    # | '_ \| | | | '_ \| | |/ __| | '_ ` _ \ / _ \ __| '_ \ / _ \ / _` / __| #
    # | |_) | |_| | |_) | | | (__  | | | | | |  __/ |_| | | | (_) | (_| \__ \ #
    # | .__/ \__,_|_.__/|_|_|\___| |_| |_| |_|\___|\__|_| |_|\___/ \__,_|___/ #
    # |_|                                                                     #
    ###########################################################################

    #___________________________________________________________________________
    def make_txt_card(self):
        """Make text part of the datacard and dump to a file.

        - loop on processes and fill in txt card lines
        - look fr systematics
        - check if there are shapes
        """
        self.process_lines = self._get_process_lines()
        self.n_systematics, self.systematics_lines = self._get_systematics_lines()

        txt_card = """
                    Datacard for event category: {cat}
                    {card_header}

                    ------------------------------------------------------------
                    imax 1 number of bins
                    jmax {jmax} number of processes minus 1
                    kmax {kmax} number of nuisance parameters
                    ------------------------------------------------------------
                    {shapes_line}
                    ------------------------------------------------------------
                    bin          cat_{cat}
                    observation  {n_observed}
                    ------------------------------------------------------------
                    bin          {process_cat}
                    process      {process_name}
                    process      {process_number}
                    rate         {process_rate}
                    ------------------------------------------------------------
                   """.format(cat = self.d_input['category'],
                              jmax = (len(self.process_list)-1),
                              kmax = self.n_systematics,
                              shapes_line = self._get_shapes_line(),
                              n_observed = self._get_observed_rate(),
                              process_cat = self.process_lines['bin'],
                              process_name = self.process_lines['name'],
                              process_number = self.process_lines['number'],
                              process_rate = self.process_lines['rate'],
                              card_header = self.card_header
                              )

        txt_card = textwrap.dedent(txt_card)
        txt_card+= textwrap.dedent(self.systematics_lines)
        print txt_card

        file_datacard_name = self.datacard_name+'.txt'
        if self.lumi_scaling != 1.0:
            file_datacard_name = file_datacard_name.replace('.txt',
                                                            '.lumi_scale_{0:3.2f}.txt'
                                                            .format(self.lumi_scaling))

        with open(file_datacard_name, 'w') as file_datacard:
            file_datacard.write(textwrap.dedent(txt_card))
            #file_datacard.write(textwrap.dedent(self.systematics_lines))
            self.log.info('Datacard text saved: {0}'.format(file_datacard_name))

    #___________________________________________________________________________
    def make_workspace(self):
        """Make RooWorkspace and dump to a file.

        - define all the functions and variables
        - define shapes
        - fetch dataset from root-trees
        """
        #we need this for some pdf functions, e.g. RooDoubleCB whic doesn't exist
        #in plane RooFit
        gSystem.Load("$CMSSW_BASE/lib/slc5_amd64_gcc472/libHiggsAnalysisCombinedLimit.so")

        self.w = RooWorkspace('w')



        #get the RooDataset
        #self.data_obs = self.w.pdf('ggH').generate(RooArgSet(self.w.var('mass4l')),
                                                   #self._get_observed_rate())

        data_obs_path = self.d_input['observation']['source']['path'] #contains TTree
        data_obs_path_to_file = data_obs_path.split('.root')[0]+'.root' #no TTree name


        #get abspath of data_obs_path
        if self.cfg_absdir: #the reader is provided
            data_obs_path_to_file = self._get_abspath(of_file = data_obs_path_to_file,
                                                      which_is_ralative_to = self.cfg_absdir)

            data_obs_path = data_obs_path_to_file+data_obs_path.split('.root')[1]
        else:

            self.log.warn('Constructing dataset data_obs, but UniversalConfigParser '
                          'instance is unknown. We try to get the literal path'
                          'from your config: {0}'.format(data_obs_path_to_file)
                )
            if os.path.exists(data_obs_path_to_file):
                self.log.info('Dataset path {0} is valid.'.format(data_obs_path_to_file))


        #the path in the cfg is relative to cfg
        data_obs_branches = []
        for observable in self.d_input['observation']['source']['observables']:
            obs_name, is_factory_statement = self._check_factory_statement(observable, 'observable')
            data_obs_branches.append(obs_name)
            if is_factory_statement:
                self.log.debug('Adding observable {0} to the RooWorkspace.'
                               .format(observable))
                self.w.factory(observable)

        dataset_tool = ToyDataSetManager()
        self.data_obs = dataset_tool.get_dataset_from_tree(
                                                data_obs_path,
                                                tree_variables = data_obs_branches,
                                                weight = "1==1",
                                                weight_var_name=0,
                                                dataset_name = "data_obs",
                                                basket=False,
                                                category = None)
        assert self._get_observed_rate()==self.data_obs.sumEntries(), ('Mismatch between '
                'obervation in txt datacard and sum of entries in RooDataSet::data_obs')

        self.data_obs.SetNameTitle('data_obs','data_obs')

        #run all functions_and_definitions:


        #setup-level functions_and_definitions
        for statement in self._get_functions_and_definitions(self.d_input['setup']):
            self.w.factory(statement)

        #setup-0 functions_and_definitions
        for statement in self._get_functions_and_definitions(self.d_input):
            self.w.factory(statement)

        for p_id, p_setup in self.d_input['processes'].iteritems():
            #setup-1 functions_and_definitions (under process name)
            for statement in self._get_functions_and_definitions(p_setup):
                self.w.factory(statement)

            self.log.debug('Checking shape in {0}/{1}'.format(self.datacard_name, p_id))
            try:
                p_setup['shape']
            except KeyError:
                raise KeyError, ('No shape defined for process {0}. '
                                 'Define at least RooUniform:{0}(var1[var2, ...])'
                                 .format(p_id))
            else:
                if p_setup['shape']:
                    self.shapes_exist = True

                    if p_setup['shape'].lower().startswith('template'):
                        the_template = self._get_template(p_setup['shape'])
                        if self.DEBUG:
                            self.log.debug('Imported template for {0}'.format(p_id))
                            the_template.Print('v')
                    else:
                        self.w.factory(p_setup['shape'])
        self.log.debug('Printing workspace...')

        getattr(self.w,'import')(self.data_obs)
        print 20*"----"
        self.w.Print()
        print 20*"----"
        self.w.writeToFile(self.workspace_file)
        self.log.info('Datacard workspace saved: {0}'.format(self.workspace_file))

    #___________________________________________________________________________
    def set_cfg_dir(self,dir_name):
        """
        Set the path to the current cfg.

        This path is used in cases of observation and template.
        It helps to turn path relative tocfg file to path from
        current directory, or absolute path.

        If not set, None is returned and the path relative to current
        directory (or absolute) is assumed.
        """
        cfg_dir = os.path.dirname(os.path.abspath(dir_name))
        if os.path.exists(cfg_dir):
            self.cfg_absdir = cfg_dir
        else:
            raise IOError, 'PATH DOES NOT EXIST! {0}.Check your config files'.format(cfg_dir)



    #___________________________________________________________________________
    def scale_lumi_by(self, lumi_scaling):
        """
        Scales luminosity in datacards by a fixed factor.

        This can be used to get exclusion limits projections with higher
        luminosities.
        """
        self.lumi_scaling = lumi_scaling
        if self.lumi_scaling != 1.0:
            self.card_header += ('Rates in datacard are scaled by a factor of {0}'
                                 .format(self.lumi_scaling))

        self.log.debug('Rates in datacards will be scaled by a factor of {0}'
                        .format(self.lumi_scaling))

    ################################################################################
    #             _            _                        _   _               _      #
    #  _ __  _ __(_)_   ____ _| |_ ___   _ __ ___   ___| |_| |__   ___   __| |___  #
    # | '_ \| '__| \ \ / / _` | __/ _ \ | '_ ` _ \ / _ \ __| '_ \ / _ \ / _` / __| #
    # | |_) | |  | |\ V / (_| | ||  __/ | | | | | |  __/ |_| | | | (_) | (_| \__ \ #
    # | .__/|_|  |_| \_/ \__,_|\__\___| |_| |_| |_|\___|\__|_| |_|\___/ \__,_|___/ #
    # |_|                                                                          #
    ################################################################################

    #___________________________________________________________________________
    def _get_abspath(self, of_file, which_is_ralative_to):
        """
        Get abspath of_file 'of_file' which is given as path
        relative to 'which_is_ralative_to' directory.
        """

        #We need abspath of the
        previous_dir = os.getcwd()
        os.chdir(which_is_ralative_to)
        os.chdir(os.path.dirname(of_file)) #go where the file is
        of_file = os.path.join(os.getcwd(), os.path.basename(of_file))
        os.chdir(previous_dir) #come back where we started

        try:
            os.path.exists(of_file)
        except:
            raise IOError, 'There is no path: {0}'.format(of_file)
        else:
            return of_file

    #___________________________________________________________________________
    def _check_factory_statement(self, statement, statement_type='observable'):
        """
        Check if statement is a RooWSFactory-type statement.
        Return name of definition and a result flag.

        statement_type:
            1) 'observable' - expects something like mass4l[100,140]
            2) 'other' - check all other possible statement types TODO

        """
        if statement_type=='observable':
            #has to be of type: 'mass_4l[105.0,140]'
            statement = re.sub(r'\s+', '', statement)
            #p_name_vals = re.compile(r'(?P<name>(^\w+))\[(?P<vals>([0-9.]+,?){0,2})\]')
            #p_factory = re.compile(r'(^\w+)\[([0-9.]+,?){0,2}\]')
            p_name_vals = re.compile(r'(?P<name>(^\w+))\s*\[\s*(?P<vals>([0-9.]+\s*,?\s*){0,2})\s*\]')
            p_factory = re.compile(r'(^\w+)\s*\[\s*([0-9.]+\s*,?\s*){0,2}\s*\]')


            self.log.debug('Checking the factory statement {0} => {1}'
                            .format(statement, bool(p_factory.match(statement))))

            if p_factory.match(statement):
                self.log.debug('The statement {0} is a good factory observable '
                                'statement.'.format(p_factory.match(statement).group()))
                m_name_vals = p_name_vals.search(statement)
                vals = m_name_vals.group('vals')
                name = m_name_vals.group('name')
                if len(vals.split(',')) ==2: #range should be an interval
                    #self.log.debug()
                    return (name, True)
                else:
                    return (name, False)
            else: #problably only the name ofabranch was sent.
                self.log.warn('The observable is not a RooWSFactory statement.'
                              'We assume it\'s a branchname only : {0}'.format(statement))
                return (statement, False)
        else:
            self.log.warn('Statement types other than \'observable\' is not implemented.')
            return (statement, False)


    #___________________________________________________________________________
    def _get_functions_and_definitions(self,data):
        """Get list of functions_and_definitions to be defined with RooWSFactory.

        Checks if 'data' contains key 'functions_and_definitions' and returns
        list of those to be defined.
        """

        try:
            data['functions_and_definitions']
        except KeyError:
            self.log.debug(('This section of configuration has no '
                'functions_and_definitions defined. '
                'Returning empty list. Section={0}'.format(data)))
            return []
        else:
            new_fnd_list = []
            #self._flatten_list(input_list = data['functions_and_definitions'],
                               #output_list = new_fnd_list)
            flatten_list(input_list = data['functions_and_definitions'],
                        output_list = new_fnd_list)

            data['functions_and_definitions'] = new_fnd_list

            self.log.debug('functions_and_definitions: {0}'.format(new_fnd_list))
            return data['functions_and_definitions']


    #___________________________________________________________________________
    def _get_shapes_line(self):
        """Gets the line with shape
        shapes *    {cat}  {cat}.root w:$PROCESS
        """
        self.shapes_exist = False
        for p in self.process_list:
            self.log.debug('Checking for shape in {0}/{1}'.format(self.datacard_name, p))
            try:
                self.d_input['processes'][p]['shape']
            except KeyError:
                pass
            else:
                if self.d_input['processes'][p]['shape']:
                    self.shapes_exist = True
                    self.workspace_file = "{0}.input.root".format(self.datacard_name)
                    if self.lumi_scaling != 1.0:
                        self.workspace_file = self.workspace_file.replace('input',
                                                                        'lumi_scale_{0:3.2f}.input'
                                                                        .format(self.lumi_scaling))
                    break

        if self.shapes_exist:
            return "shapes *    cat_{0}  {1} w:$PROCESS".format(self.d_input['category'],
                                                                self.workspace_file)
        else:
            return "#shapes are not used - counting experiment card"

    #___________________________________________________________________________
    def _get_template(self, shape_setup, new_template_name=None):
        """Get template from histogram and make it RooHistPdf.
        """
        self.log.info('Creating RooHistPdf from given histogram.')
        all_matches = re.findall("Template::(.+?)\((.+?)\)",shape_setup)

        if new_template_name:
            template_name = new_template_name
        else:
            template_name = all_matches[0][0].strip()
        template_args = [arg.strip() for arg in all_matches[0][1].split(',')]
        assert len(template_args)>1, ('Templates need to be provided in the form: '
                                      'Template::name(obs1,[obs2,obs3], a/b/c.root/hist)')

        template_observables = template_args[:-1]
        template_path = template_args[-1] #contains histo name
        template_path_to_file = template_path.split('.root')[0]+'.root' #no TTree name

        #get abspath of template_path
        if self.cfg_absdir: #the reader is provided
            template_path_to_file = self._get_abspath(of_file = template_path_to_file,
                                                      which_is_ralative_to = self.cfg_absdir)

            template_path = template_path_to_file+template_path.split('.root')[1]
        else:

            self.log.warn('Constructing histo template, but UniversalConfigParser '
                          'instance is unknown. We try to get the literal path'
                          'from your config: {0}'.format(template_path_to_file)
                )
            if os.path.exists(template_path_to_file):
                self.log.info('Dataset path {0} is valid.'.format(template_path_to_file))


        self.log.debug('Template name: {0}, arguments: {1}'.format(template_name,
                                                                  template_args))

        #fetch the template from file
        root_helper = RootHelperBase()
        histo = root_helper.get_histogram(template_path)
        template_name_cat = template_name+'_'+self.d_input['category']

        #ral_observables = RooArgList(self.w.factory('{{0}}'.format(
                                            #string.join(template_observables,','))))

        #ras_observables = RooArgSet(ral_observables)

        ral_observables = RooArgList()
        ras_observables = RooArgSet()
        for obs in template_observables:
            if self.w.allVars().find(obs):
                ral_observables.add(self.w.var(obs))
                ras_observables.add(self.w.var(obs))
            else:
                raise NameError, "The observable '{0}' is not defined.".format(obs)

        if self.DEBUG:
            ral_observables.Print()
            ras_observables.Print()


        roo_data_hist  = RooDataHist('rdh_'+template_name_cat, template_name_cat,
                                     #ral_observables, RooFit.Import(histo,kFALSE))
                                    ral_observables, RooFit.Import(histo,False))

        roo_hist_pdf   = RooHistPdf(template_name,template_name,
                                    ras_observables,
                                    roo_data_hist)


        getattr(self.w,'import')(roo_hist_pdf)

        return self.w.pdf(roo_hist_pdf.GetName())


    #___________________________________________________________________________
    def _get_processes(self, process_type='signal,background'):
        """Read the input dictionary, count processes and return
        list of processes.

        process_type: string containg keywords 'signal', 'background'
        """
        sig_process_list = []
        bkg_process_list = []
        process_list=[]
        for p_id, p_setup in self.d_input['processes'].iteritems():
            if p_setup['is_signal']:
                sig_process_list.append(p_id)
            else:
                bkg_process_list.append(p_id)

        if 'signal' in process_type.lower():
            process_list+=sorted(sig_process_list)
        if 'background' in process_type.lower():
            process_list+=sorted(bkg_process_list)

        return process_list

    #___________________________________________________________________________
    def _get_process_lines(self):
        """
        Gets and formats lines corresponding to processes from self.process_list
        """
        process_lines = {'bin': '', 'name':'', 'number':'', 'rate':'','sys':''}

        signal_process_dict = dict(enumerate(self.signal_process_list,
                                             start=-(len(self.signal_process_list)-1)))
        bkg_process_dict    = dict(enumerate(self.bkg_process_list, start=1))


        #constructing the lines
        is_first = True
        for p_number in sorted(signal_process_dict.keys()):
            #delimiter = '\t\t'
            delimiter = ' '
            if is_first:
                delimiter = ''
                is_first = False
            p_name = signal_process_dict[p_number]
            p_setup = self.d_input['processes'][p_name]
            process_lines['bin']    += ( delimiter + 'cat_' + str(self.d_input['category']))
            process_lines['name']   += ( delimiter + str(p_name) )
            process_lines['number'] += ( delimiter + str(p_number) )
            process_lines['rate']   += ( delimiter + str(float(p_setup['rate'])  *
                                                         self.lumi_scaling) )
            #process_lines['sys']     = "#systematics line: not implemented yet!!!"

        for p_number in sorted(bkg_process_dict.keys()):
            #delimiter = '\t\t'
            delimiter = ' '
            if is_first:
                delimiter = ''
                is_first = False
            p_name = bkg_process_dict[p_number]
            p_setup = self.d_input['processes'][p_name]
            process_lines['bin']    += ( delimiter + 'cat_' + str(self.d_input['category']))
            process_lines['name']   += ( delimiter + str(p_name) )
            process_lines['number'] += ( delimiter + str(p_number) )
            process_lines['rate']   += ( delimiter + str(float(p_setup['rate']) *
                                                         self.lumi_scaling) )
            #process_lines['sys']     = "#systematics line: not implemented yet!!!"


        return process_lines

    #___________________________________________________________________________
    def _get_observed_rate(self):
        """Read the data from trees and applies a cut.
        So far, we only get rate directly as a number.
        """
        return self.d_input['observation']['rate']



    #___________________________________________________________________________
    def _get_systematics_lines(self):
        """Find systematics and construct a table/dict
        """
        self.log.info('Extracting systematics.')

        systematics_lines_list = []

        sys_dict = self._get_systematics_dict()
        #loop on keys, i.e. sys names and append value if process found, otherwise, append '-'
        for sys_id in sys_dict.keys():
            values = []
            for sig_id in self.signal_process_list:
                try:
                    value = sys_dict[sys_id][sig_id]
                except KeyError:
                    value = '-'
                values.append(str(value))

            for bkg_id in self.bkg_process_list:
                try:
                    value = sys_dict[sys_id][bkg_id]
                except KeyError:
                    value = '-'
                values.append(str(value))

            if sys_dict[sys_id]['type'].startswith('param'): values=[]
            systematics_lines_list.append('{0} {1} {2}'.format(sys_id,
                                                               sys_dict[sys_id]['type'],
                                                               string.join(values,' ') ))
            #show the last one
            self.log.debug('Systematic line: {0} '.format(systematics_lines_list[-1]))


        systematics_lines = ''
        n_systematics = 0
        for line in systematics_lines_list:
            systematics_lines += line
            systematics_lines += '\n'
            n_systematics += 1
        return (n_systematics, systematics_lines)


    #___________________________________________________________________________
    def _get_systematics_dict(self):
        """Find systematics and construct a dict.

        Updates for systematics are treated.
        Finally, dict of format is constructed:
        {sys1_name:
            type: lnN
            p1: 1.04
            p2: 1.05
         sys2_name:
            ...
        }
        """
        self.log.info('Building systematics input dictionary.')

        sys_inputs = self.d_input['systematics']

        #Picking up from 'systematics' section. It can be a pure dict or a list
        #of dicts
        if isinstance(sys_inputs, dict):
            sys_dict = self._reduce_to_expected_systematic_dict(nd.nested_dict(sys_inputs))

        elif isinstance(sys_inputs, list):
            sys_dict = nd.nested_dict()
            for sys_input in sys_inputs:
                self.pp.pprint(sys_input)
                #sys_dict = update_leaf(sys_dict, sys_input)
                sys_dict.update(self._reduce_to_expected_systematic_dict(nd.nested_dict(sys_input)))
        else:
            sys_dict = nd.nested_dict()

        #Now we have a plane systematics dictionary, but still,
        #something might be defined under processes. We update with that.
        for proc_id in self.process_list:

            try:
                proc_sys = self.d_input['processes'][proc_id]['systematics']
            except KeyError:
                continue  #go to next process
            else:
                for sys_id, sys_value in proc_sys.iteritems():
                    #{name:{
                        #type:XXX
                        #p1: XXX
                        #p2: XXX}}

                    #check if this sys exists, and check the type
                    if sys_id in sys_dict.keys():
                        sys_type = str(sys_value).split()[0]
                        sys_size = str(sys_value).split()[1:]  #everything else

                        assert sys_dict[sys_id]['type'].split()[0]== sys_type,(
                        'Systematics type needs to be the same as in existing dictionary!'
                        'Otherwise you will mix-up the systematics for other processes.\n'
                        'So, the systematic type under processes section should be '
                        'the same as one already provided within systematics section.\n'
                        'Systematic {0}.type is Old:{1} New:{2}. Make them the same or just '
                        'create a new systematic error name.'
                        .format(sys_id, sys_dict[sys_id]['type'].split()[0], sys_type)
                        )

                        if sys_type.startswith('param'):
                            if sys_dict[sys_id]['type'] != sys_value:
                                self.log.warn(
                                    'You are replacing an existing parametric '
                                    'systematic <{0}> with <{1}>.\n'
                                    'Are you sure you want to do that?!'
                                    .format(sys_dict[sys_id]['type'],sys_value)
                                    )
                            sys_dict[sys_id]['type'] = sys_value
                        else:
                            sys_dict[sys_id][proc_id] = float(sys_size[0])

                    else: #this sys_id is not present in the dictionary
                        sys_dict[sys_id] = {}
                        sys_type = str(sys_value).split()[0]
                        sys_size = str(sys_value).split()[1:]  #everything else

                        if sys_type.startswith('param'):
                            sys_dict[sys_id]['type'] = sys_value
                        else:
                            sys_dict[sys_id]['type'] = sys_type
                            sys_dict[sys_id][proc_id] = float(sys_size[0])
        self.d_input['systematics'] = sys_dict.to_dict()
        return self.d_input['systematics']


    #___________________________________________________________________________
    def _reduce_to_expected_systematic_dict(self, sys_dict):
        """
        Reduce new_sys dictionary to dict typicalfor systematics.

        E.g. The systematic dict that is produced looks like:
        {   'cms_eff_e': {   'WH': 1.046,
                        'ggH': 1.046,
                        'type': 'lnN'},
        'cms_eff_m': {   'WH': 1.026,
                        'ttH': 1.026,
                        'type': 'lnN'}}

        Where the input dictionary (new_sys) looked like this:
        {'cms_eff_e': {   'UnTagged': {   'WH': 1.046,
                                            'ttH': 1.046,
                                            'type': 'lnN'}},
        'cms_eff_m': {   'UnTagged': {   'WH': 1.026,
                                        'ttH': 1.026,
                                        'type': 'lnN'}}}
        """
        self.log.debug('Removing uncesary keys from systematics dict.')

        flat_sys_dict = nd.flatten(sys_dict)
        #check that the flatten dict has more than 1 key in tuple
        for tuple_key in flat_sys_dict.keys():
            assert len(tuple_key)>=2, ('Wrong format of systematics dictionary. '
                                    'Should be sys_name:process_sys_size')
        keys_set = set([key[:-1] for key in flat_sys_dict.keys()])
        #make sure that all the sys_names are different, and that all the
        assert len(keys_set)==len(set(item[0] for item in keys_set)), (
                        'Wrong format of systematics dictionary. '
                        'You might be picking same systematics for '
                        'different categories. Be careful!')

        assert len(set(item[1:] for item in keys_set))==1, (
                        'Wrong format of systematics dictionary. '
                        'You might be selecting more categories. '
                        'Be careful!')
        #now remove all keys between first and last in flat_sys_dict.keys()
        flat_sys_dict_reduced = nd.nested_dict()
        for tuple_key, value in flat_sys_dict.iteritems():
            #it is safe to remove intermediate keys.
            if tuple_key[-1] not in self.process_list and tuple_key[-1] !='type':
                continue
            reduced_tuple_key = (tuple_key[0], tuple_key[-1])
            flat_sys_dict_reduced[reduced_tuple_key] = value

        return nd.unflatten(flat_sys_dict_reduced)


#_______________________________________________________________________________
#_______________________________________________________________________________

def parseOptions():

    usage = ('usage: %prog [options] \n'
             + '%prog -h for help')
    parser = optparse.OptionParser(usage)
    parser.add_option(''  , '--cfg', dest='config_filename', type='string',
                      default="build_datacards_from_dict.yaml",
                      help='Name of the file with full configuration')
    parser.add_option('-c', '--category', dest='category', type='string',
                      default = None,
                      help=('Name of the section/category from yaml cfg file to be run. '
                            'We produce one datacards  txt/workspace pair per section. '
                            'If not specified we assume that we process the whole '
                            'config_filename.'))
    parser.add_option('-s', '--scale_lumi_by', dest='scale_lumi_by', type='float',
                      default=1.0,    help='Scale luminosity in cards by this factor.')
    parser.add_option('-v', '--verbosity', dest='verbosity', type='int',
                      default=10, help=('Set the levelof output for all the subscripts. '
                          'Default [10] --> very verbose'))

    # store options and arguments as global variables
    global opt, args
    (opt, args) = parser.parse_args()


def main():
    parseOptions()
    #read configuration
    #set the verbosity at all levels (all Loggers)
    os.environ['PYTHON_LOGGER_VERBOSITY'] =  str(opt.verbosity)
    cfg_reader = UniversalConfigParser(file_list = opt.config_filename)
    pp = pprint.PrettyPrinter(indent=4)
    full_config = cfg_reader.get_dict()

    #datacard_name = os.path.basename(opt.config_filename).rstrip('.yaml')
    datacard_name = os.path.splitext(os.path.basename(opt.config_filename))[0]
    datacard_builder = LegoCards(datacard_input = full_config,
                                 datacard_name = datacard_name)

    datacard_builder.set_cfg_dir(opt.config_filename)
    datacard_builder.scale_lumi_by(opt.scale_lumi_by)
    datacard_builder.make_txt_card()
    datacard_builder.make_workspace()

    #dump the final cnfiguration to yaml,json (will be used to display as webage)
    #filename_full_cfg = os.path.join('full_configs/',os.path.basename(opt.config_filename))
    filename_full_cfg = os.path.splitext(opt.config_filename)[0]+'_full_cfg'
    cfg_reader.dump_to_yaml(filename_full_cfg+'.yaml', full_config)
    cfg_reader.dump_to_json(filename_full_cfg+'.json', full_config)





if __name__=="__main__":
    main()
