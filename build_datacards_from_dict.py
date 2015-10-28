#!/usr/bin/env python

#-----------------------------------------------
# Author:   Roko Plestina (IHEP-CAS), 2015
# Purpose:
#    - building "combine" datacards from dictionaries[category/final_state][process]
#-----------------------------------------------
import sys,os
import optparse
import pprint, textwrap
import string

from ROOT import RooWorkspace, RooArgSet,gSystem

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))
from lib.util.Logger import *
from lib.util.UniversalConfigParser import UniversalConfigParser

class DatacardBuilder(object):
    """
    Class for building datacards, both textual and workspace part

    EXAMPLE_____________________________________________________________
    #*** HEADER ***
    imax 1 number of bins
    jmax 5 number of processes minus 1
    kmax 14 number of nuisance parameters
    ----------------------------------------------------------------------------------------------------------------------------------
    shapes *    ch1  hzz4l_2e2muS_8TeV_xs_SM_125_mass4l_v3.Databin0.root w:$PROCESS
    ----------------------------------------------------------------------------------------------------------------------------------
    bin          ch1
    observation  8.0
    #***PER-PROCESS INFORMATION ***
    ----------------------------------------------------------------------------------------------------------------------------------
    bin                                   ch1               ch1               ch1               ch1               ch1               ch1
    process                               trueH2e2muBin0_8  bkg_zjets_8       bkg_ggzz_8        bkg_qqzz_8        out_trueH_8       fakeH_8
    process                               0                 1                 2                 3                 4                 5
    rate                                  1.0000            1.0526            0.3174            5.7443            1.0000            0.5684
    ----------------------------------------------------------------------------------------------------------------------------------
    CMS_eff_e               lnN           1.046             -                 1.046             1.046             1.046             1.046

    EXAMPLE_____________________________________________________________

    """
    def __init__(self, datacard_name, datacard_input):
        self.my_logger = Logger()
        self.log = self.my_logger.getLogger(self.__class__.__name__, 10)
        self.DEBUG = self.my_logger.is_debug()
        self.pp = pprint.PrettyPrinter(indent=4)

        #

        self.datacard_name = datacard_name
        self.d_input = datacard_input
        self.log.debug('Datacard: {0} Datacard input: {1}'.format(self.datacard_name, self.d_input))

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

    def make_txt_card(self):
        """Make text part of the datacard and dump to a file.
            - loop on processes and fill in txt card lines
        """
        self.process_lines = self._get_process_lines()
        self.n_systematics, self.systematics_lines = self._get_systematics_lines()

        txt_card = """
                    Datacard for event category: {cat}
                    {card_header}

                    ---------------------------------------
                    imax 1 number of bins
                    jmax {jmax} number of processes minus 1
                    kmax {kmax} number of nuisance parameters
                    ---------------------------------------
                    {shapes_line}
                    ---------------------------------------
                    bin          cat_{cat}
                    observation  {n_observed}
                    ---------------------------------------
                    bin          {process_cat}
                    process      {process_name}
                    process      {process_number}
                    rate         {process_rate}
                    ---------------------------------------
                   """.format(cat = self.datacard_name,
                              jmax = (len(self.process_list)-1),
                              kmax = self.n_systematics,
                              shapes_line = self._get_shapes_line(),
                              n_observed = self._get_observation(),
                              process_cat = self.process_lines['bin'],
                              process_name = self.process_lines['name'],
                              process_number = self.process_lines['number'],
                              process_rate = self.process_lines['rate'],
                              #process_systematics = self.systematics_lines,
                              card_header = self.card_header
                              )

        txt_card = textwrap.dedent(txt_card)
        txt_card+= textwrap.dedent(self.systematics_lines)
        print txt_card
        file_datacard_name = self.datacard_name+'.txt'
        if self.lumi_scaling != 1.0:
            file_datacard_name = file_datacard_name.replace('.txt', '.lumi_scale_{0:3.2f}.txt'.format(self.lumi_scaling))

        with open(file_datacard_name, 'w') as file_datacard:
            file_datacard.write(textwrap.dedent(txt_card))
            file_datacard.write(textwrap.dedent(self.systematics_lines))
            self.log.info('Datacard saved: {0}'.format(file_datacard_name))



    def _get_shapes_line(self):
        """
        Gets the line with shape
        shapes *    {cat}  {cat}.root w:$PROCESS
        """
        self.shapes_exist = False
        for p in self.process_list:
            self.log.debug('Checking for shape in {0}/{1}'.format(self.datacard_name, p))
            try:
                self.d_input[p]['shape']
            except KeyError:
                pass
            else:
                if self.d_input[p]['shape']:
                    self.shapes_exist = True
                    self.shapes_output_file = "{0}.input.root".format(self.datacard_name)
                    if self.lumi_scaling != 1.0:
                        self.shapes_output_file = self.shapes_output_file.replace('input','lumi_scale_{0:3.2f}.input'.format(self.lumi_scaling))
                    break

        if self.shapes_exist:
            return "shapes *    cat_{cat}  {shapes_output_file} w:$PROCESS".format(cat = self.datacard_name, shapes_output_file = self.shapes_output_file)
        else:
            return "#shapes are not used - counting experiment card"



    def _get_processes(self, process_type='signal,background'):
        """Read the input dictionary and count processes.
        """
        sig_process_list = []
        bkg_process_list = []
        process_list=[]
        for p in self.d_input.keys():
            if p not in self.not_a_process:
                if self.d_input[p]['is_signal']:
                    sig_process_list.append(p)
                else:
                    bkg_process_list.append(p)

        if 'signal' in process_type.lower():
            process_list+=sorted(sig_process_list)
        if 'background' in process_type.lower():
            process_list+=sorted(bkg_process_list)

        return process_list


    def _get_process_lines(self):
        """
        Gets and formats lines coresponding to processes from the self.process_list
        """
        process_lines = {'bin': '', 'name':'', 'number':'', 'rate':'','sys':''}
        #get enumerates from signal and background processes
        #signal_process_list = []
        #bkg_process_list = []
        #for p in self.process_list:
            #if self.d_input[p]['is_signal']:
                #signal_process_list.append(p)
            #else:
                #bkg_process_list.append(p)

        #self.signal_process_list = sorted(signal_process_list)
        #self.bkg_process_list = sorted(bkg_process_list)

        signal_process_dict = dict(enumerate(self.signal_process_list, start=-(len(self.signal_process_list)-1)))
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
            process_lines['bin']    += ( delimiter + 'cat_' + str(self.datacard_name) )
            process_lines['name']   += ( delimiter + str(p_name) )
            process_lines['number'] += ( delimiter + str(p_number) )
            process_lines['rate']   += ( delimiter + str(float(self.d_input[p_name]['rate'])  * self.lumi_scaling) )
            process_lines['sys']     = "#systematics line: not implemented yet!!!"

        for p_number in sorted(bkg_process_dict.keys()):
            #delimiter = '\t\t'
            delimiter = ' '
            if is_first:
                delimiter = ''
                is_first = False
            p_name = bkg_process_dict[p_number]
            process_lines['bin']    += ( delimiter + 'cat_' + str(self.datacard_name) )
            process_lines['name']   += ( delimiter + str(p_name) )
            process_lines['number'] += ( delimiter + str(p_number) )
            process_lines['rate']   += ( delimiter + str(float(self.d_input[p_name]['rate']) * self.lumi_scaling) )
            process_lines['sys']     = "#systematics line: not implemented yet!!!"


        return process_lines


    def _get_observation(self):
        """
        Read the data from trees and applies a cut.
        So far, we only get rate directly as a number.
        """
        return self.d_input['observation']['rate']

    def _get_systematics_lines(self):
        """
        Find systematics and construct a table/dict
        """
        systematics_lines_list = []
        sys_dict = self.d_input['systematics']
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
            systematics_lines_list.append('{0} {1} {2}'.format(sys_id, sys_dict[sys_id]['type'],string.join(values,' ') ))

            self.log.debug('Systematic line: {0} '.format(systematics_lines_list[-1]))        #show the last one


        systematics_lines = ''
        n_systematics = 0
        for line in systematics_lines_list:
            systematics_lines += line
            systematics_lines += '\n'
            n_systematics += 1
        return (n_systematics, systematics_lines)


    def make_workspace(self):
        """Make RooWorkspace and dump to a file"""

        gSystem.AddIncludePath("-I$CMSSW_BASE/src/ ");
        gSystem.Load("$CMSSW_BASE/lib/slc5_amd64_gcc472/libHiggsAnalysisCombinedLimit.so");
        gSystem.AddIncludePath("-I$ROOFITSYS/include");



        self.w = RooWorkspace('w')
        #run all functions_and_definitions:
        for factory_statement in self.d_input['functions_and_definitions']:
            self.w.factory(factory_statement)

        for p in self.process_list:
            self.log.debug('Checking for shape in {0}/{1}'.format(self.datacard_name, p))
            try:
                self.d_input[p]['shape']
            except KeyError:
                pass
            else:
                if self.d_input[p]['shape']:
                    self.shapes_exist = True
                    self.w.factory(self.d_input[p]['shape'])
        self.log.debug('Printing workspace...')

        self.data_obs = self.w.pdf('ggH').generate(RooArgSet(self.w.var('mass4l')), self._get_observation())

        self.data_obs.SetNameTitle('data_obs','data_obs')
        getattr(self.w,'import')(self.data_obs)
        if self.DEBUG:
            print 20*"----"
            self.w.Print()
            print 20*"----"
        self.w.writeToFile(self.shapes_output_file)
        self.log.debug('Datacard workspace written to {0}'.format(self.shapes_output_file))


    def scale_lumi_by(self, lumi_scaling):
        """
        Scales luminosity in datacards by a fixed factor. This can be
        used to get exclusion limits projections with higher luminosities.
        """
        self.lumi_scaling = lumi_scaling
        if self.lumi_scaling != 1.0:
            self.card_header+='Rates in datacard are scaled by a factor of {0}'.format(self.lumi_scaling)

        self.log.debug('Rates in datacards will be scaled by a factor of {0}'.format(self.lumi_scaling))




def parseOptions():

    usage = ('usage: %prog [options] \n'
             + '%prog -h for help')
    parser = optparse.OptionParser(usage)
    parser.add_option(''  , '--cfg', dest='config_filename', type='string', default="build_datacards_from_dict.yaml",    help='Name of the file with full configuration')
    parser.add_option('-c', '--category', dest='category', type='string', default="ALL",    help='Name of the section/category from yaml cfg file to be run. We produce one datacards  txt/workspace pair per section.')
    parser.add_option('-s', '--scale_lumi_by', dest='scale_lumi_by', type='float', default=1.0,    help='Scale luminosity in cards by this factor.')
    parser.add_option('-v', '--verbosity', dest='verbosity', type='int', default=10, help='Set the levelof output for all the subscripts. Default [10] = very verbose')

    # store options and arguments as global variables
    global opt, args
    (opt, args) = parser.parse_args()


def main():
    parseOptions()
    #read configuration
    os.environ['PYTHON_LOGGER_VERBOSITY'] =  str(opt.verbosity) #will be checked/used by all Loggers
    cfg_reader = UniversalConfigParser(cfg_type="YAML",file_list = opt.config_filename)
    pp = pprint.PrettyPrinter(indent=4)
    full_config = cfg_reader.get_dict()

    categories = opt.category.split(',')
    for cat in categories:
        datacard_builder = DatacardBuilder(datacard_name = cat , datacard_input = full_config[cat])
        pp.pprint(full_config[cat])
        datacard_builder.scale_lumi_by(opt.scale_lumi_by)
        datacard_builder.make_txt_card()
        datacard_builder.make_workspace()

if __name__=="__main__":
    main()
