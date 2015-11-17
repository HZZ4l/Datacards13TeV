#-------------------------------------------------------------------------------
# Author:   Roko Plestina (IHEP-CAS),
#           2013-2014
# Purpose:
#    - embedd any dataset from tree
#    - embedd toys into workspace
#    - produce toys datasets from MC by selecting events.
#-------------------------------------------------------------------------------
import sys, os, pprint
from ROOT import RooAbsData, RooArgSet, RooArgList, RooDataSet
from ROOT import RooFit, RooWorkspace, RooRealVar, gSystem
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))
from lib.util.Logger import Logger
from lib.RootHelpers.RootHelperBase import RootHelperBase


class ToyDataSetManager(RootHelperBase):

    def __init__(self):
        """Initialize whatever is needed"""
        self.my_logger = Logger()
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

        #make RooRealVars from tree_variables
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

