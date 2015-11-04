#!/usr/bin/env python
#-----------------------------------------------
# Author:   Roko Plestina (IHEP-CAS),
#           2013-2014
# Purpose:
#    - embedd toys into workspace
#    - produce toys datasets from MC by selecting events.
#-----------------------------------------------
import sys, os
import optparse
import pprint
import string
from ROOT import *


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))
import lib.util.MiscTools as misc
from lib.util.Logger import *
from lib.RootHelpers.RootHelperBase import RootHelperBase
import collections
class ToyDataSetManager(RootHelperBase):

    def __init__(self):
        """Initialize whatever is needed"""
        self.my_logger = Logger()
        #self.log = Logger().getLogger(self.__class__.__name__, 10)
        self.log = self.my_logger.getLogger(self.__class__.__name__, 10)
                        #}
        self.DEBUG = self.my_logger.is_debug()
        self.pp = pprint.PrettyPrinter(indent=4)

        #initialize RooFit
        gSystem.Load("libHiggsAnalysisCombinedLimit.so")
        self.output_filename = 'worskapce_with_embedded_toys.root'



    def set_toys_path(self,toys_path):
        """
        Set the path for the toy dataset.There is aleays one active toy held in self.toys.
        """
        self.toys_path = toys_path
        self.toys = self.get_object(path = toys_path, object_type = RooAbsData,  clone=False)


    def set_workspace_path(self,ws_path):
        """
        Set the path for the workspace where toys will be included.
        There is only one workspace that can be active in the class.
        """
        self.ws = self.get_object(path = ws_path, object_type = RooWorkspace,  clone=False)

    def set_output_file_name(self,output_filename):
        """
        Set the name of the output root file.
        """
        self.output_filename = output_filename


    def set_new_toys_name(self, new_toys_name):
        """
        Set name for toys in the workspace
        """
        self.new_toys_name = new_toys_name


    def import_toys_to_ws(self, ws_path = None, toys_path = None, output_filename = None, new_toys_name = None):
        """
        Imports a given toys dataset (or multiple toys) into the workspace and dumps to new root file.

        Parameters:
        -----------
        ws_path   : path to exisitng workspace (string)
        toys_path : path or list of paths to toys.TODO add regexp parsing to import matching toys.
        output_filename : file name of the output workspace
        new_toys_name : in case of one toy import, a new name can be set. In case of list, the name is set
                        to be the same as in the source file.

        Returns:
        --------
        Returns 0 in case it goes trough without erorrs(?).

        """
        #TODO set checks for the input provided
        if ws_path:
            self.set_workspace_path(ws_path)

        if output_filename:
            self.set_output_file_name(output_filename)
        if new_toys_name:
            self.set_new_toys_name(new_toys_name)

        try:
            self.ws
        except AttributeError:
            raise AttributeError, 'You need to provide workspace path.'



        if toys_path:
            toys_path_list = []
            if isinstance(toys_path,list):
                toys_path_list = toys_path
            elif isinstance(toys_path,str):
                toys_path_list = [toys_path]

            for the_toy in toys_path_list:
                self.set_toys_path(the_toy)
                toys_name = self.get_paths(the_toy)[-1]  #just getthe name of toys object in the root file.
                self.log.info('Setting toys name in workspace to: {0}'.format(toys_name))
                self.set_new_toys_name(toys_name)
                self.toys.SetName(self.new_toys_name)
                getattr(self.ws,'import')(self.toys)
                self.log.info("Imported DataSet '{0}' into workspace '{1}'.".format(self.toys.GetName(), self.ws.GetName()))
        else:
            try:
                self.toys
            except AttributeError:
                raise AttributeError, 'You need to provide toys path.'

            try:
                self.new_toys_name
            except AttributeError:
                toys_name = self.get_paths(self.toys_path)[-1]  #just getthe name of toys object in the root file.
                self.log.info('Setting toys name in workspace to: {0}'.format(toys_name))
                self.set_new_toys_name(toys_name)

            self.toys.SetName(self.new_toys_name)
            getattr(self.ws,'import')(self.toys)
            self.log.info("Imported DataSet '{0}' into workspace '{1}'.".format(self.toys.GetName(), self.ws.GetName()))

        self.ws.data(self.toys.GetName()).Print()
        self.ws.data(self.toys.GetName()).Print("v")

        #write workspace
        self.ws.writeToFile(self.output_filename)
        self.log.info("Writing workspace '{0}' to file {1}".format(self.ws.GetName(), self.output_filename))

        return 0

    def set_dataset_name(self, dataset_name):
        """
        Set name of the dataset in workspace.
        """
        self.dataset_name = dataset_name

    def import_dataset_to_ws(self, dataset, workspace, output_filename = None, new_name = None):
        """
        Import dataset to worspace workspace.
        """
        if new_name:
            dataset.SetName(new_name)
        if output_filename:
            self.set_output_file_name(output_filename)


        self.log.info("Imported DataSet '{0}' into workspace '{1}' and written to file {2}.".format(dataset.GetName(), workspace.GetName(), self.output_filename))
        pass

    def set_workspace(self,workspace):
        """
        Provide workspace from path naload it to self.ws or
        provide directly workspace and load it to self.ws
        """
        if isinstance(workspace,RooWorkspace):
            self.ws = workspace
            self.log.debug('Loaded in workspace {0}.'.format(self.ws.GetName()))
        elif isinstance(workspace,str):
            self.set_workspace_path(self,workspace)
            self.log.debug('Loaded in workspace {0} from path: '.format(workspace))


    def dump_datasets_to_file(self,output_filename = None, access='RECREATE'):
        """
        Write all datasets collected in the basket(RootHelperBase) to a file.
        """
        if output_filename:
            self.set_output_file_name(output_filename)
        self.dump_basket_to_file(self.output_filename, access)
        self.log.info('All items from the basket have been written to file: {0}'.format(self.output_filename))
        return 0


    def get_dataset_from_tree(self,path_to_tree, tree_variables, weight = "1==1", weight_var_name=0, dataset_name = "my_dataset", basket=True, category = None):
        """
        Creates RooDataSet from a plain root tree given:
        - variables name list
        - weight expression. It works in the same way as TTree cut.
        Returns:
        --------
        - RooDataSet
        - also fills the basket with datasets (basket inhereted from RootHelperBase class)

        TODO
        ----
        - add implementation for category setting(check in prepare_toy_datasets_for_sync)
            - check if adding toy dataset to each channel workspace individually behaves well
              after combineCards.py.
        """

        #make RooRelVars from tree_variables
        my_arg_set = RooArgSet()
        my_rrv = dict()
        for var_name in tree_variables:
            #TODO implement check that branch exist
            my_rrv[var_name] = RooRealVar(var_name,var_name,-999999999,999999999)
            my_arg_set.add(my_rrv[var_name])
        if self.DEBUG:
            self.log.debug('RooArgSet is now:')
            my_arg_set.Print()

        #get the tree from path_to_tree
        my_tree = self.get_TTree(path_to_tree, cut = weight)
        self.log.debug('Selected tree contains {0} events'.format(my_tree.GetEntries()))
        #create RooDataSet and reduce tree if needed
        #self.dataset_from_tree =  RooDataSet(dataset_name, dataset_name, my_tree, my_arg_set, weight).reduce(my_arg_set)
        self.dataset_from_tree =  RooDataSet(dataset_name, dataset_name, my_tree, my_arg_set)
        #self.dataset_from_tree =  RooDataSet(dataset_name, dataset_name, my_tree, my_arg_set, "", weight_var_name)
        #data[j]=new RooDataSet(Form("data%d",j),Form("data%d",j),outTree,RooArgSet(rCMS_zz4l_widthKD,rCMS_zz4l_widthMass,rweightFit),"","_weight_");
        self.log.debug('RooDataSet contains {0} events'.format(self.dataset_from_tree.sumEntries()))
        #.reduce(ROOT.RooArgSet(self.D0))
        self.current_arg_set = my_arg_set

        #add dataset to basket
        if basket:
            self.add_to_basket(self.dataset_from_tree, new_name = dataset_name, new_title = dataset_name)

        return self.dataset_from_tree

    def get_current_arg_set(self):
        """
        Return last dataset setup used by get_dataset_from_tree().
        """
        return self.current_arg_set


def prepare_toy_datasets_for_sync():
    #parseOptions()
    DEBUG = False
    if opt.verbosity!=10:
        os.environ['PYTHON_LOGGER_VERBOSITY'] =  str(opt.verbosity)
    if opt.verbosity >=4:
        DEBUG = True



    #1) RooDataSet with all processes for one sqrts and final state
    #- have RooCategory for sqrts and final state
        #chan  = [1_7, 2_7, 3_7, 1_8,2_8,3_8]
        #cat.defineType(chan[j],j); j=0..6
        #cat.setLabel(chan[j]);
    #2) finally append all toys to same RooDataSet

    log = Logger().getLogger("prepare_toy_datasets_for_sync", 10)

    toy_manager = ToyDataSetManager()
    #toy_manager.set_workspace_path(opt.ws_path)
    #path_to_tree, tree_variables, weight = "1", dataset_name = "my_dataset"):
    #shapes *        ch1_ch1  hzz4l_4muS_7TeV.input.root w:$PROCESS
    #shapes *        ch1_ch2  hzz4l_4eS_7TeV.input.root w:$PROCESS
    #shapes *        ch1_ch3  hzz4l_2e2muS_7TeV.input.root w:$PROCESS
    #shapes *        ch2_ch1  hzz4l_4muS_8TeV.input.root w:$PROCESS
    #shapes *        ch2_ch2  hzz4l_4eS_8TeV.input.root w:$PROCESS
    #shapes *        ch2_ch3  hzz4l_2e2muS_8TeV.input.root w:$PROCESS

    #model = "trees_v3/bkg_only"
    #model = "trees_v3/bkg_only/zjets"
    #model = "trees_v3/bkg_only/qqZZ"
    #model = "trees_v3/bkg_only/ggZZ"

    model = "trees_v3/SM"
    #model = "trees_v3/Mixed_fa3"
    #model = "trees_v3/Mixed_fa2"

    #model = "trees_v2/SM"
    #model = "trees_v2/Mixed_fa3"
    #model = "trees_v2/Mixed_fa2"

    #model = "trees_v0/SM"
    #model = "trees_v0/Mixed_fa3"
    #model = "trees_v0/Mixed_fa2"

    toys_dir = "/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/CMSdata/SYNC/{0}".format(model)

    #Christoys:
    #toys_dir = "/afs/cern.ch/work/c/chmartin/public/ForEmbedded/Final_v2/"

    chan_path_dict = {
            'ch1_ch1' :  "{0}/Toys_CJLSTntuple_7TeV_4mu_*.root/ToyEvents".format(toys_dir),
            'ch1_ch2' :  "{0}/Toys_CJLSTntuple_7TeV_4e_*.root/ToyEvents".format(toys_dir),
            'ch1_ch3' :  "{0}/Toys_CJLSTntuple_7TeV_2e2mu_*.root/ToyEvents".format(toys_dir),
            'ch2_ch1' :  "{0}/Toys_CJLSTntuple_8TeV_4mu_*.root/ToyEvents".format(toys_dir),
            'ch2_ch2' :  "{0}/Toys_CJLSTntuple_8TeV_4e_*.root/ToyEvents".format(toys_dir),
            'ch2_ch3' :  "{0}/Toys_CJLSTntuple_8TeV_2e2mu_*.root/ToyEvents".format(toys_dir)
        }
    pp = pprint.PrettyPrinter(indent=4)
    #if DEBUG:
        #log.debug('Initial dictionary:')
        #pp.pprint(chan_path_dict)
    channel_name = sorted(chan_path_dict.keys())
    cat = RooCategory("CMS_channel","CMS_channel")
    for cat_idx, cat_name in enumerate( channel_name ):
            cat.defineType(cat_name,cat_idx);
            cat.setLabel(cat_name);
    if DEBUG:
            log.debug('Category : {0}'.format(cat_idx))
            cat.Print('v')

    my_vars = []
    if ("fa3" in model) and ("fa2" in model):
        my_vars = ['D_bkg','D_0m','D_cp', 'D_0hp','D_int','Weight','ZZMass']
    elif "fa3" in model:
        my_vars = ['D_bkg','D_0m','D_cp','Weight','ZZMass']
    elif "fa2" in model:
        my_vars = ['D_bkg', 'D_0hp','D_int','Weight','ZZMass']
    else:
        my_vars = ['D_bkg','D_0m','D_cp', 'D_0hp','D_int','Weight','ZZMass']

    my_rrv = dict()
    my_rrv['D_bkg']     = RooRealVar('D_bkg','D_bkg', 0,1.)


    my_rrv['D_0m']      = RooRealVar('D_0m','D_0m', 0,1.)
    my_rrv['D_cp']      = RooRealVar('D_cp','D_cp', -0.5,0.5)

    my_rrv['D_0hp']      = RooRealVar('D_0hp','D_0hp', 0,1.)
    my_rrv['D_int']      = RooRealVar('D_int','D_int', -0.2,1)

    my_rrv['ZZMass']    = RooRealVar('ZZMass','ZZMass', 100,1000.)
    my_rrv['Weight']    = RooRealVar('Weight','Weight', 1.)


    #my_rrv['D_bkg'].setBins(2)
    my_rrv['D_bkg'].setBins(50)
    my_rrv['D_0m'].setBins(50)
    my_rrv['D_cp'].setBins(50)
    my_rrv['D_0hp'].setBins(50)
    my_rrv['D_int'].setBins(50)



    my_arg_set = RooArgSet()
    for var_name in my_vars:
        #TODO implement check that branch exist
        #my_rrv[var_name] = RooRealVar(var_name,var_name,-999999999,999999999)
        my_arg_set.add(my_rrv[var_name])
    my_arg_set.add(cat)
    if DEBUG:
        log.debug('RooArgSet is now:')
        my_arg_set.Print('v')



    if os.path.exists(opt.output_filename):
        log.debug("Removing file: {0}".format(opt.output_filename))
        os.remove(opt.output_filename)

    ###run on all toys
    #for idx in range(0,1000):  #run on toy numbers
        #log.debug('Running on toy number : {0}'.format(idx))


        ##run on each channel (sqrts+finalstate)
        #for cat_idx, cat_name in enumerate( channel_name ):
            #my_path_to_tree = chan_path_dict[cat_name]
            #log.debug("my_path_to_tree:  {0}".format(my_path_to_tree ))

            #the_dataset = toy_manager.get_dataset_from_tree(path_to_tree = my_path_to_tree, tree_variables=my_vars,
                                                            #weight="ToyNumber=={0} && (ZZMass>105.6 && ZZMass<140.6)".format(idx),
                                                            #dataset_name="toys/toy_{0}_{1}".format(idx,cat_idx), basket = False)
            #the_dataset_with_cat = RooDataSet(the_dataset.GetName(),the_dataset.GetName(), my_arg_set, RooFit.Index(cat),RooFit.Import(cat_name,the_dataset))

            #log.debug('RooDataSet the_dataset_with_cat contains {0} events'.format(the_dataset_with_cat.sumEntries()))
            #if cat_idx==0:
                #combined_dataset = the_dataset_with_cat
            #else:
                #combined_dataset.append(the_dataset_with_cat)

        #log.debug('RooDataSet combined_dataset contains {0} events'.format(combined_dataset.sumEntries()))
        #combined_dataset.Print("v")
        #toy_manager.add_to_basket(combined_dataset, new_name = "toys/comb_{0}".format(idx), new_title = "toys/comb_{0}".format(idx))
        #toy_manager.dump_datasets_to_file(opt.output_filename,'UPDATE')  #this one can receive both

    import lib.RootHelpers.RootHelperBase as rhb
    root_helper = rhb.RootHelperBase()


    my_arg_set = RooArgSet()
    for var_name in my_vars:
        #TODO implement check that branch exist
        #my_rrv[var_name] = RooRealVar(var_name,var_name,-999999999,999999999)
        my_arg_set.add(my_rrv[var_name])
    my_arg_set.add(cat)
    if DEBUG:
        log.debug('RooArgSet is now:')
        my_arg_set.Print('v')

    #import asimov dataset
    for cat_idx, cat_name in enumerate( channel_name ):
            my_path_to_tree = chan_path_dict[cat_name]
            log.debug("my_path_to_tree: {0} ".format(my_path_to_tree ))

            the_dataset = toy_manager.get_dataset_from_tree(path_to_tree = my_path_to_tree, tree_variables = my_vars,
                                                                  weight="(ZZMass<140.6&&ZZMass>105.6)", dataset_name="toys/toy_asimov_v0_{0}".format(cat_idx), basket = False, weight_var_name = "Weight")
            #mass_column = RooFormulaVar("CMS_zz4l_mass","CMS_zz4l_mass", "ZZMass", RooArgList(my_rrv['ZZMass']))
            #the_dataset.addColumn(mass_column)
            #my_arg_set.add(mass_column)

            #my_tree = root_helper.get_TTree(my_path_to_tree, cut = "(ZZMass<140.6&&ZZMass>105.6)")
            #log.debug('Selected tree contains {0} events'.format(my_tree.GetEntries()))
            #the_dataset  =  RooDataSet("toys/toy_asimov_v0_{0}".format(cat_idx), "toys/toy_asimov_v0_{0}".format(cat_idx), my_tree, my_arg_set, "", "Weight")

            the_dataset_with_cat = RooDataSet("toys/toy_asimov_{0}".format(cat_idx),"toys/toy_asimov_{0}".format(cat_idx), my_arg_set, RooFit.Index(cat), RooFit.Import(cat_name,the_dataset), RooFit.WeightVar("Weight"))


            #the_dataset_with_cat = RooDataSet(the_dataset.GetName(),the_dataset.GetName(), my_arg_set, RooFit.Index(cat),RooFit.Import(cat_name,the_dataset))
            log.debug('RooDataSet the_dataset_with_cat contains {0} events'.format(the_dataset_with_cat.sumEntries()))
            the_dataset_with_cat.Print()
            if cat_idx==0:
                combined_dataset = the_dataset_with_cat
            else:
                combined_dataset.append(the_dataset_with_cat)

    log.debug('RooDataSet combined_dataset contains {0} events'.format(combined_dataset.sumEntries()))
    combined_dataset.Print()
    combined_dataset.Print("v")
    toy_manager.add_to_basket(combined_dataset, new_name = "toys/embedded_asimov", new_title = "toys/embedded_asimov")
    toy_manager.dump_datasets_to_file(opt.output_filename,'UPDATE')  #this one can receive both


def prepare_asimov_toy_datasets_for_sync():
    #parseOptions()
    DEBUG = False
    if opt.verbosity!=10:
        os.environ['PYTHON_LOGGER_VERBOSITY'] =  str(opt.verbosity)
    if opt.verbosity >=4:
        DEBUG = True



    #1) RooDataSet with all processes for one sqrts and final state
    #- have RooCategory for sqrts and final state
        #chan  = [1_7, 2_7, 3_7, 1_8,2_8,3_8]
        #cat.defineType(chan[j],j); j=0..6
        #cat.setLabel(chan[j]);
    #2) finally append all toys to same RooDataSet

    log = Logger().getLogger("prepare_toy_datasets_for_sync", 10)

    toy_manager = ToyDataSetManager()
    #toy_manager.set_workspace_path(opt.ws_path)
    #path_to_tree, tree_variables, weight = "1", dataset_name = "my_dataset"):
    #shapes *        ch1_ch1  hzz4l_4muS_7TeV.input.root w:$PROCESS
    #shapes *        ch1_ch2  hzz4l_4eS_7TeV.input.root w:$PROCESS
    #shapes *        ch1_ch3  hzz4l_2e2muS_7TeV.input.root w:$PROCESS
    #shapes *        ch2_ch1  hzz4l_4muS_8TeV.input.root w:$PROCESS
    #shapes *        ch2_ch2  hzz4l_4eS_8TeV.input.root w:$PROCESS
    #shapes *        ch2_ch3  hzz4l_2e2muS_8TeV.input.root w:$PROCESS



    model = "trees_SM"
    #model = "trees_Mix_fa2"
    #model = "trees_Mix_fa3"
    toys_dir = "/afs/cern.ch/user/r/roko/wd_datacards/CreateFullSimToys/{0}".format(model)

    #Christoys:
    #toys_dir = "/afs/cern.ch/work/c/chmartin/public/ForEmbedded/Final_v2/"

    #chan_path_dict = {
            #'ch1_ch1' :  "{0}/Toys_CJLSTntuple_7TeV_4mu_*.root/SelectedTree".format(toys_dir),
            #'ch1_ch2' :  "{0}/Toys_CJLSTntuple_7TeV_4e_*.root/SelectedTree".format(toys_dir),
            #'ch1_ch3' :  "{0}/Toys_CJLSTntuple_7TeV_2e2mu_*.root/SelectedTree".format(toys_dir),
            #'ch2_ch1' :  "{0}/Toys_CJLSTntuple_8TeV_4mu_*.root/SelectedTree".format(toys_dir),
            #'ch2_ch2' :  "{0}/Toys_CJLSTntuple_8TeV_4e_*.root/SelectedTree".format(toys_dir),
            #'ch2_ch3' :  "{0}/Toys_CJLSTntuple_8TeV_2e2mu_*.root/SelectedTree".format(toys_dir)
        #}
        
    chan_path_dict = {
        'ch1_ch1' :  "{0}/DTree_7TeV_4mu_*.root/selectedEvents".format(toys_dir),
        'ch1_ch2' :  "{0}/DTree_7TeV_4e_*.root/selectedEvents".format(toys_dir),
        'ch1_ch3' :  "{0}/DTree_7TeV_2e2mu_*.root/selectedEvents".format(toys_dir),
        'ch2_ch1' :  "{0}/DTree_8TeV_4mu_*.root/selectedEvents".format(toys_dir),
        'ch2_ch2' :  "{0}/DTree_8TeV_4e_*.root/selectedEvents".format(toys_dir),
        'ch2_ch3' :  "{0}/DTree_8TeV_2e2mu_*.root/selectedEvents".format(toys_dir)
    }
    
    pp = pprint.PrettyPrinter(indent=4)
    #if DEBUG:
        #log.debug('Initial dictionary:')
        #pp.pprint(chan_path_dict)
    channel_name = sorted(chan_path_dict.keys())
    cat = RooCategory("CMS_channel","CMS_channel")
    for cat_idx, cat_name in enumerate( channel_name ):
            cat.defineType(cat_name,cat_idx);
            cat.setLabel(cat_name);
    if DEBUG:
            log.debug('Category : {0}'.format(cat_idx))
            cat.Print('v')

    my_vars = []
    if ("fa3" in model) and ("fa2" in model):
        my_vars = ['D_bkg','D_0m','D_cp', 'D_0hp','D_int','Weight','mass4l']
    elif "fa3" in model:
        my_vars = ['D_bkg','D_0m','D_cp','Weight','mass4l']
    elif "fa2" in model:
        my_vars = ['D_bkg', 'D_0hp','D_int','Weight','mass4l']
    else:
        my_vars = ['D_bkg','D_0m','D_cp', 'D_0hp','D_int','Weight','mass4l']

    my_rrv = dict()
    my_rrv['D_bkg']     = RooRealVar('D_bkg','D_bkg', 0,1.)


    my_rrv['D_0m']      = RooRealVar('D_0m','D_0m', 0,1.)
    my_rrv['D_cp']      = RooRealVar('D_cp','D_cp', -0.5,0.5)

    my_rrv['D_0hp']      = RooRealVar('D_0hp','D_0hp', 0,1.)
    my_rrv['D_int']      = RooRealVar('D_int','D_int', -0.2,1)

    my_rrv['mass4l']    = RooRealVar('mass4l','mass4l', 100,1000.)
    my_rrv['Weight']    = RooRealVar('Weight','Weight', 1.)


    my_rrv['D_bkg'].setBins(5)
    #my_rrv['D_bkg'].setBins(50)
    my_rrv['D_0m'].setBins(50)
    my_rrv['D_cp'].setBins(50)
    my_rrv['D_0hp'].setBins(50)
    my_rrv['D_int'].setBins(50)



    my_arg_set = RooArgSet()
    for var_name in my_vars:
        #TODO implement check that branch exist
        #my_rrv[var_name] = RooRealVar(var_name,var_name,-999999999,999999999)
        my_arg_set.add(my_rrv[var_name])
    my_arg_set.add(cat)
    if DEBUG:
        log.debug('RooArgSet is now:')
        my_arg_set.Print('v')



    if os.path.exists(opt.output_filename):
        log.debug("Removing file: {0}".format(opt.output_filename))
        os.remove(opt.output_filename)

    import lib.RootHelpers.RootHelperBase as rhb
    root_helper = rhb.RootHelperBase()


    my_arg_set = RooArgSet()
    for var_name in my_vars:
        #TODO implement check that branch exist
        #my_rrv[var_name] = RooRealVar(var_name,var_name,-999999999,999999999)
        my_arg_set.add(my_rrv[var_name])
    my_arg_set.add(cat)
    if DEBUG:
        log.debug('RooArgSet is now:')
        my_arg_set.Print('v')

    #import asimov dataset
    for cat_idx, cat_name in enumerate( channel_name ):
            my_path_to_tree = chan_path_dict[cat_name]
            log.debug("my_path_to_tree: {0} ".format(my_path_to_tree ))

            the_dataset = toy_manager.get_dataset_from_tree(path_to_tree = my_path_to_tree, tree_variables = my_vars,
                                                                  weight="(mass4l<140.6&&mass4l>105.6)", dataset_name="toys/toy_asimov_v0_{0}".format(cat_idx), basket = False, weight_var_name = "Weight")

            the_dataset_with_cat = RooDataSet("toys/toy_asimov_{0}".format(cat_idx),"toys/toy_asimov_{0}".format(cat_idx), my_arg_set, RooFit.Index(cat), RooFit.Import(cat_name,the_dataset), RooFit.WeightVar("Weight"))
            log.debug('RooDataSet the_dataset_with_cat contains {0} events'.format(the_dataset_with_cat.sumEntries()))
            the_dataset_with_cat.Print()
            if cat_idx==0:
                combined_dataset = the_dataset_with_cat
            else:
                combined_dataset.append(the_dataset_with_cat)

    log.debug('RooDataSet combined_dataset contains {0} events'.format(combined_dataset.sumEntries()))
    combined_dataset.Print()
    combined_dataset.Print("v")
    #combined_dataset.SetNameTitle("toys/embedded_asimov","toys/embedded_asimov")
    #toy_manager.add_to_basket(combined_dataset)
    toy_manager.add_to_basket(combined_dataset, new_name = "toys/embedded_asimov", new_title = "toys/embedded_asimov")
    toy_manager.dump_datasets_to_file(opt.output_filename,'UPDATE')  #this one can receive both


#######################################
#examples for ToyDataSetManager usaage:
#######################################
def add_dataset_from_tree():
    #parseOptions()

    if opt.verbosity!=10:
        os.environ['PYTHON_LOGGER_VERBOSITY'] =  str(opt.verbosity)

    #if not opt.input_tree:
        #raise RuntimeError, 'Missing path to root tree. Check help!'


    toy_manager = ToyDataSetManager()
    #toy_manager.set_workspace_path(opt.ws_path)
    #path_to_tree, tree_variables, weight = "1", dataset_name = "my_dataset"):
    for idx in range(0,1000):
        #file_selection = "/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/CMSdata/SYNC/toys_SM/toys_7and8TeV_2e2mu_*.root/ToyEvents"
        #file_selection = "*4mu_*.root/ToyEvents"
        #toy_manager.get_dataset_from_tree(path_to_tree=file_selection,tree_variables=['D_bkg','D_0m','D_cp'], weight="ToyNumber=={0}".format(idx), dataset_name="toys/toy_{0}".format(idx))
        toy_manager.get_dataset_from_tree(path_to_tree=opt.input_tree,tree_variables=['D_bkg','D_0m','D_cp'], weight="ToyNumber=={0}".format(idx), dataset_name="toys/toy_{0}".format(idx))

    toy_manager.dump_datasets_to_file(opt.output_filename,'RECREATE')  #this one can receive both




def addToyDataset_MC():
    """
    Embedd any dataset to any datacard workspace.
    """
    
    parseOptions()
    if opt.verbosity!=10:
        os.environ['PYTHON_LOGGER_VERBOSITY'] =  str(opt.verbosity)

    #if not opt.ws_path:
        #raise RuntimeError, 'Missing path to workspace. Check help!'
    #if not opt.toys_path:
        #raise RuntimeError, 'Missing path to toys. Check help!'


    workspace_dir = '/afs/cern.ch/user/r/roko/wd_datacards/cards_3D.k3k1.D0M.Dint13.Dbkg.7and8TeV.M4lWin40GeV.CJLSTtemplates.geolocating.fulltmpl/HCG/125.6/'
    workspace_dir = '/afs/cern.ch/user/r/roko/wd_datacards/cards_3D.k3k1.D0M.Dint13.Dbkg.7and8TeV.M4lWin40GeV.CJLSTtemplates.geolocating.fulltmpl.2e2muyield/HCG/125.6/'
    workspace_dir = '/afs/cern.ch/user/r/roko/wd_datacards/cards_3D.k3k1.D0M.Dint13.Dbkg.7and8TeV.M4lWin40GeV.CJLSTtemplates.geolocating.fulltmpl.2e2muyield.newpdf/HCG/125.6/'
    workspace_dir = '/afs/cern.ch/user/r/roko/wd_datacards/cards_3D.k2k1.D0Ph.Dint12.Dbkg.Dbkg.7and8TeV.M4lWin40GeV.CJLSTtemplates.geolocating.fulltmpl.2e2muyield.newpdf.shapesys/HCG/125.6/'
    workspace_dir = '/afs/cern.ch/user/r/roko/wd_datacards/cards_3D.k2k1.D0Ph.Dint12.Dbkg.7and8TeV.M4lWin40GeV.geolocating.fulltmpl.2e2muyieldEndpoints/HCG/125.6/'
    workspace_dir = '/afs/cern.ch/user/r/roko/wd_datacards/cards_3D.k2k1.D0Ph.Dint12.Dbkg.7and8TeV.M4lWin40GeV.geolocating.fulltmpl.2e2muyieldEndpoints.2e2muFactorsFromPaper.fixedGammasByHand.YR3/HCG/125.6/'
    workspace_dir = '/afs/cern.ch/user/r/roko/wd_datacards/cards_3D.k2k1.7and8TeV.2e2muyield.2e2muFactorsFromPaper.fixedGammasByHand.YR3/HCG/125.6/'
    workspace_dir = '/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/cards_3D.k2k1.7and8TeV.2e2muyieldEndpoints.denomGenLevel.2e2muFactorsFromPaper.fixedGammasByHand.YR3/HCG/125.6/'
    #September 19
    workspace_dir = '/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/cards_3D.k2k1.7and8TeV.BUFshapes.2e2muyieldEndpoints.denomGenLevel.2e2muFactorsFromPaper.factorsRecoOld/HCG/125.6/'
    workspace_dir = '/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/cards_3D.k2k1.7and8TeV.BUFshapes.2e2muyieldEndpoints.denomGenLevel.2e2muFactorsFromPaper.factorsRecoNew/HCG/125.6/'
    
    #October 14
    workspace_dir = '/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/cards_3D.k2k1.7and8TeV.BUFshapes.2e2muyieldEndpoints.denomGenLevel.2e2muFactorsFromPaper.factorsRecoNew/HCG/125.6/'
    workspace_dir = '/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/cards_3D.k3k1.7and8TeV.BUFshapes.2e2muyieldEndpoints.denomGenLevel.2e2muFactorsFromPaper.factorsRecoOld/HCG/125.6/'
    
    
    #October 15
    workspace_dir = '/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/cards_3D.k2k1.7and8TeV.BUFshapes.factorsRecoNew.reducedBins/HCG/125.6/'
    #workspace_dir = '/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/cards_3D.k3k1.7and8TeV.BUFshapes.factorsRecoOld.reducedBins/HCG/125.6/'
    
    #October 15
    workspace_dir = '/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/cards_3D.k2k1.7and8TeV.BUFshapesNoSmoothing.factorsRecoNew.reducedBins.nativeSamples/HCG/125.6/'
    workspace_dir = '/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/cards_3D.k3k1.7and8TeV.BUFshapesNoSmoothing.factorsRecoOld.reducedBins.nativeSamples/HCG/125.6/'
    
    ##----------------------------
    #####make a big list of paths
    path_list = []
    #path_list.append('/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/CMSdata/SYNC/asimov_toys/embedded_asimov_SM_Oct15_reducedBins.root/toys/embedded_asimov')
    path_list.append('/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/CMSdata/SYNC/asimov_toys/embedded_asimov_SM_Oct14.root/toys/embedded_asimov')
    toy_manager = ToyDataSetManager()
    toy_manager.set_workspace_path('{0}combine.ws.4l.v1.root/w'.format(workspace_dir))
    toy_manager.set_output_file_name('{0}ws.toys_SM_v3.root'.format(workspace_dir))
    toy_manager.import_toys_to_ws(toys_path = path_list)  #this one can receive both parameters
    del toy_manager
    ##----------------------------
    
    if "k2k1" and "k3k1" in workspace_dir:
        print "Do we have the toys for mixed fa2 and fa3 together. "
        
    elif "k2k1" in workspace_dir:
        ####MixedaddToyDataset_MC
        path_list = []
        #path_list.append('/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/CMSdata/SYNC/asimov_toys/embedded_asimov_Mix_fa2_Oct15_reducedBins.root/toys/embedded_asimov')
        path_list.append('/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/CMSdata/SYNC/asimov_toys/embedded_asimov_Mix_fa2_Oct14.root/toys/embedded_asimov')
        toy_manager_2 = ToyDataSetManager()
        toy_manager_2.set_workspace_path('{0}combine.ws.4l.v1.root/w'.format(workspace_dir))
        toy_manager_2.set_output_file_name('{0}ws.toys_Mixed_fa2_v3.root'.format(workspace_dir))
        toy_manager_2.import_toys_to_ws(toys_path = path_list)  #this one can receive both parameters
        del toy_manager_2
    elif "k3k1"in workspace_dir:
        #####MixedaddToyDataset_MC
        path_list = []
        #path_list.append('/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/CMSdata/SYNC/asimov_toys/embedded_asimov_Mix_fa3_Oct15_reducedBins.root/toys/embedded_asimov')
        path_list.append('/afs/cern.ch/work/r/roko/Stat/CMSSW_611_JCP/src/HZZ4L_Combination/CombinationPy/CreateDatacards/CMSdata/SYNC/asimov_toys/embedded_asimov_Mix_fa3_Oct14.root/toys/embedded_asimov')
        toy_manager_3 = ToyDataSetManager()
        toy_manager_3.set_workspace_path('{0}combine.ws.4l.v1.root/w'.format(workspace_dir))
        toy_manager_3.set_output_file_name('{0}ws.toys_Mixed_fa3_v3.root'.format(workspace_dir))
        toy_manager_3.import_toys_to_ws(toys_path = path_list)  #this one can receive both parameters
        del toy_manager_3


def addToyDataset():
    parseOptions()

    if opt.verbosity!=10:
        os.environ['PYTHON_LOGGER_VERBOSITY'] =  str(opt.verbosity)

    if not opt.ws_path:
        raise RuntimeError, 'Missing path to workspace. Check help!'
    if not opt.toys_path:
        raise RuntimeError, 'Missing path to toys. Check help!'

    toy_manager = ToyDataSetManager()
    toy_manager.set_workspace_path(opt.ws_path)
    toy_manager.set_output_file_name(opt.output_filename)
    toy_manager.set_toys_path(opt.toys_path)
    toy_manager.import_toys_to_ws()  #this one can receive both parameters


def parseOptions():

    usage = ('usage: %prog [options] \n' + '%prog -h for help')
    parser = optparse.OptionParser(usage)
    parser.add_option('-w', '--workspace', dest='ws_path', type='string', default=None,    help='Full path to workspace <..my_file.root/w>')
    parser.add_option('-t', '--toys', dest='toys_path', type='string', default=None,    help='Full path to toy dataset<..my_file.root/toys>')
    parser.add_option('-i', '--input_tree', dest='input_tree', type='string', default=None,    help='Full path to root tree <..my_file.root/toys>')
    parser.add_option('-o', '--output', dest='output_filename', type='string', default='worskapce_with_embedded_toys.root', help='Output file name.')
    parser.add_option('-v', '--verbosity', dest='verbosity', type='int', default=10, help='Set the level of output for all the subscripts. Default [10] = very verbose')

    # store options and arguments as global variables
    global opt, args
    (opt, args) = parser.parse_args()



if __name__ == "__main__":
    parseOptions()

    addToyDataset_MC()  #use for adding RooDataSet to a workspace
    #prepare_asimov_toy_datasets_for_sync()  #use for preparing a RooDataSet from trees with "Weight" variable 