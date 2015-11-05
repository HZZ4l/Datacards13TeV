import sys, os, pwd, commands
import optparse, shlex, re
import math
import errno
import shutil
from array import array
import subprocess
from Logger import *
import collections
import fnmatch


def processCmd(cmd, verbose=True):
    ## run it ##
    if verbose:
        print get_terminal_width()*"_"
        figlet_run = """

 ____                    _                   _          _ _                      _
|  _ \ _   _ _ __  _ __ (_)_ __   __ _   ___| |__   ___| | |   ___ _ __ ___   __| |_
| |_) | | | | '_ \| '_ \| | '_ \ / _` | / __| '_ \ / _ \ | |  / __| '_ ` _ \ / _` (_)
|  _ <| |_| | | | | | | | | | | | (_| | \__ \ | | |  __/ | | | (__| | | | | | (_| |_
|_| \_\\\\__,_|_| |_|_| |_|_|_| |_|\__, | |___/_| |_|\___|_|_|  \___|_| |_| |_|\__,_(_)
                                 |___/
                """
    
        print figlet_run
        print cmd
        print get_terminal_width()*"_"
    #p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    while p.poll() is None:
        out = p.stdout.read(1)
        sys.stdout.write(out)
        sys.stdout.flush()

    rc = p.returncode
    if rc==0 :
        if verbose:
            print
            print "Done with exit code = 0: ",cmd
            print
        
            print "     __          _                  "
            print "    / /       __| | ___  _ __   ___ "
            print "__ / /       / _` |/ _ \| '_ \ / _ \\"
            print "\ V /       | (_| | (_) | | | |  __/"
            print " \_/         \__,_|\___/|_| |_|\___|"
            print




    else:
        print
        print "Command exit code =", rc,": ", cmd
        print
        if verbose:
            print "__  __       __       _ _          _ "
            print "\ \/ /      / _| __ _(_) | ___  __| |"
            print " \  /      | |_ / _` | | |/ _ \/ _` |"
            print " /  \      |  _| (_| | | |  __/ (_| |"
            print "/_/\_\     |_|  \__,_|_|_|\___|\__,_|"
            print
        sys.exit()

def make_sure_path_exists(path) :
    if not path:
        return
    try:
        os.makedirs(path)
    except OSError, exception:
        if exception.errno != errno.EEXIST:
            raise


def force_symlink(file1, file2):
    try:
        os.symlink(file1, file2)
    except OSError, e:
        if e.errno == errno.EEXIST:
            os.remove(file2)
            os.symlink(file1, file2)


def grep(what, where_list):
    import re, sys, glob
    #for arg in sys.argv[2:]:
    where_list = [f.strip() for f in where_list.split(",")]
    #print "----- Grep for what={0} and where={1}".format(what, where_list)
    grep_list=[]
    for arg in where_list:
        #print glob.glob(arg.strip())
        for file in glob.glob(arg.strip()):
            for line in open(file, 'r'):
                    if re.search(what, line):
                        grep_list.append(line.strip())
                        #print "line"line,
    return grep_list


class AttrDict(dict):
    """
    Useful when you want to access dictionary members like attributes.
    Caveat is that you can only have ordinary strings as keys - otherwise it breakes.
    """
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

def recursive_update(dict_to_update, dict_with_update):
    """
    Updates a dict dict_to_update with dict dict_with_update but
    in infinite depth without replacing values from dict_to_update
    that are not defined in dict_with_update
    """
    for k, v in dict_with_update.iteritems():
        if isinstance(v, collections.Mapping):
            r = recursive_update(dict_to_update.get(k, {}), v)
            dict_to_update[k] = r
        else:
            dict_to_update[k] = dict_with_update[k]
    return dict_to_update


def return_filenames(rootdir,searchstring) :
    """
    Get list of files matching regexp searchstring from all subdirs.
    """
    fileslist = []
    for folders,subs,files in os.walk(rootdir):
        for fi in files:
            fullpath = os.path.join(folders,fi)
            if ".root" in fi: fileslist.append(fullpath)
    if searchstring: fileslist=filter(lambda x: searchstring in x,fileslist)
    return fileslist


def get_file_list(file_regexp_list, in_dir):
    """
    Get list of files matching list of regexps
    """
    files_list=[]
    raw_file_list = file_regexp_list #can contain regexp --> we want to expend to list
    if isinstance(raw_file_list, str):
        raw_file_list= [raw_file_list]
    for regexp in raw_file_list:
        print 'Regexp for files : {0} '.format(regexp)
        files_list+= fnmatch.filter(os.listdir(in_dir), regexp)
    print 'Returning files list: {0}'.format(files_list)
    return files_list

def AreSame(a, b, tolerance=None):
    if tolerance==None:
        import sys
        tolerance = sys.float_info.epsilon
    return abs(a - b) < tolerance


def belongsTo(value, rangeStart, rangeEnd):
    if value >= rangeStart and value <= rangeEnd:
        return True
    return False


def filterPick(list,the_regexp=None):
    """
    Return a list filtered with a regexp.
    """
    if the_regexp:
        filter = re.compile(the_regexp).search
    else:
        return []
    return [ ( l, m.group(1) ) for l in list for m in (filter(l),) if m]

    #theList = ["foo", "bar", "baz", "qurx", "bother"]
    #searchRegex = re.compile('(a|r$)').search
    #x = filterPick(theList,searchRegex)



def make_list_of_strings(list_or_str):
    assert isinstance(list_or_str, list) or isinstance(list_or_str, str), "[MiscTools.make_list] Argument should be either list of strings or string with \";:, \" as delimiters. "
    if isinstance(list_or_str, list):
        list_of_strings = [str(item) for item in list_or_str]
    elif isinstance(list_or_str, str):
        import re
        list_or_str = re.sub('[;:,]+',',',list_or_str)
        list_of_strings = list_or_str.split(",")
    #print "[MiscTools.make_list]", list_of_strings
    return list_of_strings


def get_terminal_width():
    """
    Get number of chars that can fit into current terminal
    """
    import console
    return console.getTerminalSize()[0]

def get_ranges(n_entries, n_ranges, first=0):
    """
    Get ranges (n_ranges) in 2D-tuple for integer n_entries starting from the 'first'.
    """
    ranges_list = []
    n_jobs_mod = n_entries - n_ranges* (n_entries/n_ranges)
    #print n_jobs_mod
    f = first
    l = f+(n_entries/n_ranges)-1

    for i in range(n_ranges):
        #add points that are leftover starting from the first range.
        if n_jobs_mod>0:
            l+=1
            n_jobs_mod-=1
        ranges_list.append((f,l))
        #print f, l
        f = l+1
        l = f+(n_entries/n_ranges)-1

    return ranges_list


def figlet_boxes(text, figlet=True, figlet_opt="-t", boxes=False, boxes_opt="-d shell"):
    """
    Prints figlet style messages like:
     _____ _       _      _   
    |  ___(_) __ _| | ___| |_ 
    | |_  | |/ _` | |/ _ \ __|
    |  _| | | (_| | |  __/ |_ 
    |_|   |_|\__, |_|\___|\__|
              |___/            
    - figlet=True the figlet will be drawn.
    - boxes=True the box will be drawn around the text.
    """
    
    figlet_cmd=""
    if figlet:
        figlet_cmd+=("| figlet "+figlet_opt)
        
    boxes_cmd=""
    if boxes:
        boxes_cmd+=("| boxes "+boxes_opt)
        
    processCmd("echo {0} {1} {2}".format(text,figlet_cmd,boxes_cmd), False)
    
    