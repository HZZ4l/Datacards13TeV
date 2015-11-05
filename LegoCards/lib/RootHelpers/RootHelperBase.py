#!/usr/bin/env python

#-----------------------------------------------
# Author:   Roko Plestina (IHEP-CAS),
#           2013-2014
# Purpose:
#    - basic manipulation with files, root objects ...
#    - pick any object from path, change it and then dump to a file
#-----------------------------------------------
import sys, os
import optparse
import pprint
import copy
import string
#from array import array
from ROOT import *
import collections


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))
from lib.util.Logger import *
import lib.util.MiscTools as misc
#from  lib.util.UniversalConfigParser import UniversalConfigParser


class RootHelperBase(object):
    """
    Class that helps to pick any object from any root file
    by specifiying the path to the object like:
    path/to/root_file.root/path/to/root_object.
    Class can also check for type of object and return TypeError
    in case the object is not of a desired type.
    """

    def __init__(self):
        self.log = Logger().getLogger(self.__class__.__name__, 10)
        self.pp = pprint.PrettyPrinter(indent=4)
        self.DEBUG = True

    def check_in_opened_files_table(self, file_name,access):
        """
        Makes a check in the open_files_table dictionary and returns
        pointer to the file if file is opened correct access mode.

        Returns:
        --------
        tuple (is_opened, pointer_to_file).
        In case file doesn't exist (is_opened=False,pointer_to_file=None)

        """
        try:
            self.open_files_table[file_name][access]
        except KeyError:
            self.log.debug('File {0} is not opened in {1} mode.'.format(file_name, access))
            return (False, None)
        else:
            the_file = self.open_files_table[file_name][access]
            if isinstance(the_file,TFile):
                if (the_file.IsOpen() and not the_file.IsZombie()):
                    self.log.debug('File {0} is already opened in {1} mode. Return pointer to file.'.format(file_name, access))
                    return (True, the_file)
                else:
                    self.log.debug('File {0}   in {1} mode is either closed or zombie.'.format(file_name, access))
                    self.open_files_table[file_name][access] = None
                    return (False, None)
            else:
                self.log.debug('File {0} is not opened in {1} mode.'.format(file_name, access))
                return (False, None)

    def update_opened_files_table(self, file_object, access):
        """
        Update the status of files opened.
        file_name: acces : file_pointer structure.
        """
        try:
            self.open_files_table
        except AttributeError:
            #self.open_files_table = collections.OrderedDict()
            self.open_files_table = {}
            self.open_files_table[file_object.GetName()] = {access : file_object}
        else:

            try:
                self.open_files_table[file_object.GetName()]
            except KeyError:
                self.open_files_table[file_object.GetName()] = {access : file_object}
            else:
                self.open_files_table[file_object.GetName()].update({access : file_object})
            #self.open_files_table['dummy'].update({access : file_object})
            #self.open_files_table[file_object.GetName()][access] = file_object

        if self.DEBUG:
            self.pp.pprint(self.open_files_table)

        return 0


    def TFile_safe_open(self, file_name, access = 'READ'):
        """
        Safely open TFile object. Memory is saved by cheking if the file is already
        open by looking up in the list open_files_table.

        """
        #check if file is already openedby looking-up the opend files dict
        is_opened=False
        rootfile= None
        try:
            self.open_files_table
        except AttributeError:
            pass
        else:
            is_opened, rootfile = self.check_in_opened_files_table(file_name,access)
        if is_opened:
            self.log.debug('Returning pointer to ROOT file: {0}'.format(file_name))
            return rootfile

        self.log.debug('Opening ROOT file: {0}'.format(file_name))

        if access.upper() == 'READ' and not os.path.exists(file_name):
            raise IOError, 'File path does not exist: {0}'.format(file_name)
        else:
            base_dir = os.path.dirname(file_name)
            misc.make_sure_path_exists(base_dir)

        rootfile = TFile.Open(file_name,access)
        self.update_opened_files_table(rootfile, access)

        if not rootfile:
            raise IOError, 'The file {0} either doesn\'t exist or cannot be open'.format(file_name)
        return rootfile


    def get_paths(self, path):
        """
        Returns tuple (path_to_root_file, path_to_root_object_in_root_file)
        """
        path_contains_file = ('.root' in path)
        path_segments = path.split('.root')
        if path.endswith('.root'):  #only root file path exists
            return (path,"")

        #print path_segments
        #assert 1<len(path_segments)<=2, 'Path should be in format <path/to/dir>root_object_file.root/path_to_root_object_in_file'
        assert 0<len(path_segments)<=2, 'Path should be in format <path/to/dir>root_object_file.root/path_to_root_object_in_file'
        path_to_file = ""
        if len(path_segments)==2: #path contains file name and object path in the root file
            path_to_file = path_segments[0]+'.root'
            self.log.debug('Src root file: {0}'.format(path_to_file ))
            #path_to_root_object = string.join(path_segments[-1].split('/')[1:],'/') #to remove the '/' after .root

        if path_segments[-1].startswith('/'):
            path_to_root_object = path_segments[-1][1:] #to remove the '/' after .root
        else:
            path_to_root_object = path_segments[-1] #there is no '/' at the beggining
        self.log.debug('Src root_object name: {0}'.format(path_to_root_object))

        return (path_to_file,path_to_root_object)


        #path_to_file = path_segments[0]+'.root'
        #self.log.debug('Src root file: {0}'.format(path_to_file ))
        #path_to_root_object = string.join(path_segments[-1].split('/')[1:],'/') #to remove the '/' after .root
        #self.log.debug('Src root_object name: {0}'.format(path_to_root_object))

        #return (path_to_file,path_to_root_object)

    def get_object(self, path, object_type=None, clone=False):
        """
        Get any root object copy from path and check it's type.
        The object is copied from the file if needed.
        """
        path_to_file, path_to_root_object = self.get_paths(path)
        root_object_file = self.TFile_safe_open(path_to_file, 'READ')
        the_object = root_object_file.Get(path_to_root_object)
        is_TTree = isinstance(the_object,TTree)
        if clone:
            if not is_TTree:
                the_object = copy.deepcopy(root_object_file.Get(path_to_root_object))
                self.log.debug('Coping root_object {0} of type={1}.'.format(path_to_root_object, type(the_object)))
                root_object_file.Close()
            else:
                #FIXME
                self.log.warn('Cloning the full tree {0}. !!! Still not fully tested !!!'.format(path_to_root_object))
                the_object = root_object_file.Get(path_to_root_object).CloneTree()
                #will not close file since it will destroy the object. Better to write the tree down first, then close file.

        else:
            self.log.debug('Pointer to root_object {0} of type={1} is returned.'.format(path_to_root_object, type(the_object)))
        return the_object

    def get_TTree(self,path , cut = None, clone = False):
        """
        Get a tree from the path of format //machine/file_name.root/subdir/tree_name.
        If path is list it will asume TChain. Wildcards can be used but ".root" has
        to exost in the path name, otherwise 'segmentation violation'
        """

        the_tree = TChain()

        if isinstance(path, list):
            tree_name = self.get_paths(path[0])[1]
            the_tree.SetName(tree_name)
            for item in path:
                assert isinstance(item,str),'The tree path should be of string format and not: {0}'.format(type(item))
                add_result = the_tree.Add(item)

        elif isinstance(path, str):
            tree_name = self.get_paths(path)[1]
            the_tree.SetName(tree_name)
            add_result = the_tree.Add(path)
        self.log.debug('TChain has been constructed from {0} files with correct tree names.'.format(add_result))
        if cut:
            assert isinstance(cut, str), 'The TTree cut has to be string value, not {0} !!!'.format(type(cut))
            clone = True
            the_selection_tree = the_tree.CopyTree(cut)
            return the_selection_tree
        else:
            return the_tree


    def get_histogram(self,path, hist_type = TH1, clone = False):
        """
        Get TH1 object or any other that inherits from TH1
        """
        return self.get_object(path,hist_type, clone)

    def get_embedded_object(self, path_to_container, container_type = None, embedded_object = None, object_type = None, clone = False):
        """
        Get an object embedded into another class, like e.g. a TH1 from TCanvas
        saved in file. In case only path_to_container is given, it will return the container
        like with get_object method.
        """
        pass

    def add_to_basket(self,root_object, new_name = None, new_title = None):
        """
        Add object to the basket with new_name and new_title.
        If new_name contains "/" then a directory will be created inside the file. (TODO)
        """

        if new_name:
            #name_in_basket = new_name
            new_name_no_subfolders = new_name.split('/')[-1]  #remove subfolder name from the new_name
            root_object.SetName(new_name_no_subfolders)
            name_in_basket = new_name
        else:
            name_in_basket = root_object.GetName()


        if new_title:
            root_object.SetTitle(new_title)
        try:
            self.root_fruit_basket
        except AttributeError:
            self.root_fruit_basket = collections.OrderedDict()
            self.log.debug('Creating new root-object basket.')
        else:
            if self.DEBUG and len(self.root_fruit_basket)<10:
                self.log.debug('Adding root-object to existing basket. Basket state (printed if less then 10 items):')
                self.pp.pprint(self.root_fruit_basket)
        self.root_fruit_basket[name_in_basket] = root_object


    def _get_subfolders_and_name(self,path):
        """
        Gives back the 2 element tuple with subfolder path and a name of root_object
        """
        path_segments = path.split('/')
        assert len(path_segments)>0, 'The name should not be empty string.'
        if len(path_segments) > 1:
            #check if first is '/'
            if path_segments[0]=='': path_segments.pop(0)
            subfolders = string.join(path_segments[:-1],'/')
            root_object_name = path_segments[-1]
            self.log.debug('Root-subfolder: {0}'.format(subfolders))
            self.log.debug('Root-object name: {0}'.format(root_object_name))
            return (subfolders, root_object_name)
        else:
            root_object_name = path_segments[-1]
            return (None, root_object_name)

    def _get_directory(self,root_file, path):
        """
        Create and cd to the directory if given like a/b/c
        """
        root_file.cd()
        #subfolders = self._get_subfolders_and_name(path)[0]
        if path:
            self.log.debug('Creating root-subfolder {0}'.format(path))
            mkdir_res = root_file.mkdir(path)
            self.log.info('Root-subfolder {0} created with code = {1}'.format(path, mkdir_res))
            root_file.cd(path)
        else:  #no subfolder will be created
            root_file.cd()
        self.log.debug('Current directory: {0}'.format(gDirectory.GetPath()))


    def flush_basket(self):
        """
        Resets the basket content and delets the basket.
        """

        try:
            del self.root_fruit_basket
        except:
            raise RuntimeError, 'Basket cannot be flushed and destroyed! It even doesn\'t exist ...'
        else:
            self.log.info('Basket flushed!')
            return 0

    def dump_basket_to_file(self, file_name, access = 'UPDATE'):
        """
        Save what is in basket to a file. Create directories in the path if needed.
        """
        out_file = self.TFile_safe_open(file_name, access)
        out_file.cd()
        if self.DEBUG:
            self.pp.pprint(self.root_fruit_basket)

        for item_name in self.root_fruit_basket.keys():
            subfolders, root_object_name = self._get_subfolders_and_name(item_name)
            self._get_directory(out_file, subfolders)  #it will create and cd to the directory if given like a/b/c
            self.log.debug('Writing root-object: {0} Object name: {1} ; Object title: {2}'.format(self.root_fruit_basket[item_name],self.root_fruit_basket[item_name].GetName(),self.root_fruit_basket[item_name].GetTitle()))
            is_TTree = isinstance(self.root_fruit_basket[item_name],TTree)
            if is_TTree:
                self.log.debug('This is a TTree object : {0}'.format(self.root_fruit_basket[item_name]))
                copy_tree_name = self.root_fruit_basket[item_name].GetName()
                copy_tree_title = self.root_fruit_basket[item_name].GetTitle()
                tree_for_saving = self.root_fruit_basket[item_name].CloneTree(0)
                copy_res = tree_for_saving.CopyEntries(self.root_fruit_basket[item_name])
                tree_for_saving.SetNameTitle(copy_tree_name,copy_tree_title)
                write_res = tree_for_saving.Write()
            else:
                write_res = self.root_fruit_basket[item_name].Write()

            if write_res == 0 :
                self.log.error('The object {0} cannot be written into {1}'.format(item_name, gDirectory.GetPath()))
            else:
                self.log.info('The object {0} has been written into {1}'.format(item_name, gDirectory.GetPath()))

        out_file.Close()
        self.log.info('Saved the basket with {1} items into the file: {0}'.format(file_name, len(self.root_fruit_basket)))
        self.flush_basket()

        return 0


def main():
    helper = RootHelperBase()

if __name__=="__main__":
    main()