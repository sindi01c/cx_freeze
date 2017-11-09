

#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:et:ft=python:nowrap:sts=4:sw=4:ts=4
##############################################################################

'''
'''

##############################################################################
# Imports


from __future__ import absolute_import, print_function, unicode_literals

import lib2to3
import os
import platform
import requests
import shlex
import shutil
import string
import subprocess
import sys
import time
import appdirs, packaging
import opcode

from cx_Freeze import Executable, hooks, setup
from distutils.sysconfig import get_python_lib

distutils_path = os.path.join(os.path.dirname(opcode.__file__), 'distutils')

# https://bitbucket.org/anthony_tuininga/cx_freeze/issues/43
try:
    import numpy   # noqa
    import scipy   # noqa
except ImportError:
    pass

# https://stackoverflow.com/a/29286081
# https://bitbucket.org/anthony_tuininga/cx_freeze/pull-requests/64
# https://bitbucket.org/anthony_tuininga/cx_freeze/pull-requests/70
# https://github.com/pierreraybaut/guidata/commit/9be41d1
def load_h5py(finder, module):
    # h5py module has a number of implicit imports
    finder.IncludeModule('h5py.defs')
    finder.IncludeModule('h5py.h5ac')
    finder.IncludeModule('h5py.utils')
    finder.IncludeModule('h5py._errors')
    finder.IncludeModule('h5py._proxy')
    try:
        import h5py.api_gen  # noqa
    except ImportError:
        pass
    else:
        finder.IncludeModule('h5py.api_gen')


# https://bitbucket.org/anthony_tuininga/cx_freeze/issues/43
# https://github.com/pierreraybaut/guidata/commit/9be41d1
def load_scipy(finder, module):
    finder.IncludePackage('scipy._lib')
    finder.IncludePackage('scipy.misc')
    finder.IncludePackage('scipy.integrate')
    finder.IncludePackage('scipy.sparse')
    finder.IncludePackage('scipy.special')


hooks.load_h5py = load_h5py
hooks.load_scipy = load_scipy

class opt(object):  # noqa

    compress = True
    edition = 'Full'
    excludes = [
        'FixTk',
        'ImageTk',
        'PIL.ImageTk',
        'PIL._imagingtk',
        'Tkconstants',
        'Tkinter',
        '_imaging',
        '_imagingtk',
        'bsddb',
        'curses',
        'doctest',
        'lib2to3',
        'matplotlib.backends._backend_gdk',
        'matplotlib.backends._gtk',
        'matplotlib.backends._tkagg',
        'pdb',
        'pydoc',
        'pydoc_data',
        'pyreadline',
        'pywin.debugger',
        'pywin.debugger.dbgcon',
        'tcl',
        'test',
        'tk',
        'distutils'
    ]
    installer = (platform.system().lower() == 'darwin')
    packages = [
        'analysisengine',
        'compass',
        'dataexports',
        'datavalidation',
        'filterpype',
        'filterpypefds',
        'flightdataaircrafttables',
        'flightdataparametertree',
        'flightdataplotgenerator',
        'flightdataplotter',
        'flightdataprofiles',
        'flightdataprocessing',
        'flightdatarunner',
        'flightdatautilities',
        'hdfaccess',
        'lflconversion',
        'polarisconfiguration',
        'utilities',
        # dependencies:
        'geomag>=0.9.2',
        'h5py<2.6.0',                 # https://github.com/h5py/h5py/issues/669
        'networkx!=1.10.*,!=1.11.*',  # https://github.com/networkx/networkx/issues/1775
    ]
    upgrade = False
    version = time.strftime('%y.%j.%H%M', time.gmtime())
    
    python_dir = os.path.dirname(sys.executable)
    build_dir = os.path.join('build', 'exe.%s-%s' % (sys.platform, '%s.%s' % sys.version_info[:2]))
    inject = [
        'analyser_custom_hooks.py',
        'analyser_custom_hooks.pyc',
        'analyser_custom_settings.py',
        'analyser_custom_settings.pyc',
    ]

# XXX: Compatibility issue with ipython (jsonschema) on Python 2.7:
if sys.version_info.major == 2:
    opt.excludes += ['collections.abc', 'collections.sys']    
    
    # TODO - Should be done something like this
    #  - http://www.davidfischer.name/2010/01/extending-distutils-for-repeatable-builds/
    filtered = []
    for arg in sys.argv:
        if arg == '--community':
            opt.edition = 'Community'
        elif arg == '--full':
            opt.edition = 'Full'
        elif arg == '--plotter':
            opt.edition = 'Plotter'
        elif arg == '--upgrade':
            opt.upgrade = True
        else:
            filtered.append(arg)
    sys.argv = filtered
    
    # Setup the internal PyPI URIs and pip upgrade the required packages.
    if opt.upgrade:
        if platform.system().lower() == 'windows':
            path0 = os.path.join(os.environ['APPDATA'], 'pip', 'pip.ini')
            path1 = os.path.expanduser('~/pydistutils.cfg')
        else:
            path0 = os.path.expanduser('~/.pip/pip.conf')
            path1 = os.path.expanduser('~/.pydistutils.cfg')
    
        try:
            os.makedirs(os.path.dirname(path0))
        except OSError:
            pass
    
        index = 'https://pypi.flightdataservices.com/simple/'
        open(path0, 'w').write('[global]\nindex-url = %s\n' % index)
        open(path1, 'w').write('[easy_install]\nindex_url = %s\n' % index)
    
        print('Upgrading packages: %s' % ' '.join(opt.packages))
        # XXX: Workaround for missing upgrade only-if-needed. See following links:
        #      - https://github.com/pypa/pip/issues/59
        #      - https://pip.pypa.io/en/stable/user_guide/#only-if-needed-recursive-upgrade
        command = shlex.split('python -m pip install --disable-pip-version-check --pre')
        subprocess.call(command + ['--no-deps', '--upgrade'] + opt.packages)
        subprocess.call(command + opt.packages)
    
    
    ##############################################################################    
    
# Helpers


# Lookup function for path in site packages:
site_packages = get_python_lib()
lookup = lambda *a: os.path.join(site_packages, *a)


##############################################################################
# Executables

# NOTE:
# - 'compiler' is required by anything using 'data_validation'.
# - 'distutils' is required by anthing using 'matplotlib' or 'h5py'.
# - 'unittest' is required by anything using 'numpy'.
# - 'socket' is required by anything using 'flightdatautilities'.

no_api = ['BaseHTTPServer', '_ssl', 'email', 'ssl', 'webbrowser']  # 'socket'
no_doc = ['docutils', 'markupsafe', 'pygments', 'sphinx']
no_gui = ['PyQt4', 'wx']
no_test = ['mock', 'nose', 'setuptools']  # 'distutils', 'unittest'
protected = ['analyser_custom_hooks', 'analyser_custom_settings', 'data_validation', 'flightdataaircrafttables', 'flightdataprofiles']

ConvertAGS = Executable(
    path=[lookup('lflconversion', 'fds_lfl')] + sys.path,
    script=lookup('lflconversion', 'fds_lfl', 'converter.py'),
    targetName='ConvertAGS',
    excludes=opt.excludes + no_api + no_doc + no_gui + no_test + ['bz2', 'compiler', 'logging'],
)

ConvertGRAF = Executable(
    path=[lookup('lflconversion', 'graf')] + sys.path,
    script=lookup('lflconversion', 'graf', 'convert.py'),
    targetName='ConvertGRAF',
    excludes=opt.excludes + no_api + no_doc + no_gui + no_test + ['bz2', 'compiler', 'logging'],
)

FlightDataReadoutValidator = Executable(
    path=[lookup('lflconversion', 'tools')] + sys.path,
    script=lookup('lflconversion', 'tools', 'check_names.py'),
    targetName='FlightDataReadoutValidator',
    excludes=opt.excludes + ['bz2', 'compiler'],
    packages=['scipy.integrate'],
)

LFLValidator = Executable(
    script=lookup('wingide', 'lfl_panel_output.py'),
    targetName='LFLValidator',
    excludes=opt.excludes + no_api + no_doc + no_gui + no_test + ['bz2', 'compiler', 'h5py', 'Image', 'IPython', 'PIL', 'simplejson', 'xml'],
)

FlightDataBitstreamAligner = Executable(
    script=lookup('filterpypefds', 'process_bitstream_file.py'),
    targetName='FlightDataBitstreamAligner',
    excludes=opt.excludes + no_api + no_doc + no_gui + no_test + ['compiler', 'hotshot', 'logging', 'xml'],
)

FlightDataAligner = Executable(
    script=lookup('filterpypefds', 'byte_align.py'),
    targetName='FlightDataAligner',
    excludes=opt.excludes + no_api + no_doc + no_gui + no_test + ['compiler', 'hotshot', 'logging', 'xml'],
)

FlightDataConverter = Executable(
    script=lookup('compass', 'compass_cli.py'),
    targetName='FlightDataConverter',
    excludes=opt.excludes + no_api + no_doc + no_gui + no_test + ['compiler', 'Image', 'IPython', 'PIL', 'xml'],
    includes=['scipy.linalg'],
)

FlightDataConverter767 = Executable(
    script=lookup('compass', 'arinc767', 'arinc767.py'),
    targetName='FlightDataConverter767',
    excludes=opt.excludes + no_api + no_doc + no_gui + no_test + ['compiler', 'Image', 'IPython', 'PIL'],
    includes=['lxml._elementpath', 'scipy.linalg'],
)

FlightDataCleanser = Executable(
    path=[lookup('data_validation')] + sys.path,
    script=lookup('data_validation', 'validate_file.py'),
    targetName='FlightDataCleanser',
    excludes=opt.excludes + no_doc + no_gui + no_test + ['Image', 'IPython', 'jinja2', 'osgeo', 'PIL', 'xml'],
    packages=['analysis_engine', 'data_validation', 'scipy.integrate.vode'],
)

FlightDataSplitter = Executable(
    script=lookup('analysis_engine', 'split_hdf_to_segments.py'),
    targetName='FlightDataSplitter',
    excludes=opt.excludes + no_doc + no_gui + no_test + ['Image', 'IPython', 'osgeo', 'PIL', 'simplekml', 'xml'],
    includes=['scipy.signal.sigtools'],
    packages=['analysis_engine'],
)

FlightDataAnalyzer = Executable(
    script=lookup('analysis_engine', 'process_flight.py'),
    targetName='FlightDataAnalyzer',
    excludes=opt.excludes + no_doc + no_gui + no_test + ['Image', 'IPython', 'jinja2', 'lib2to3', 'osgeo', 'PIL'],
    includes=['matplotlib.backends.backend_wxagg', 'scipy.integrate.vode', 'scipy.integrate.lsoda'],
    packages=['analysis_engine'],
)

FlightDataParameterTree = Executable(
    path=[lookup('flightdataparametertree')] + sys.path,
    script=lookup('flightdataparametertree', 'server.py'),
    targetName='FlightDataParameterTree',
    excludes=opt.excludes + no_doc + no_gui + no_test + protected + ['compiler', 'Image', 'IPython', 'osgeo', 'PIL'],
    includes=['flightdatautilities.browser'],
    packages=['analysis_engine', 'scipy.integrate'],
)

FlightDataPlotter = Executable(
    script=lookup('flightdataplotter', 'plot_params.py'),
    targetName='FlightDataPlotter',
    excludes=opt.excludes + no_api + no_doc + no_test + ['compiler', 'IPython', 'lib2to3', 'PIL'],
    includes=['matplotlib.backends.backend_wxagg'],
    packages=['scipy.integrate'],
)

FlightDataPlotGenerator = Executable(
    script=lookup('flightdataplotgenerator', 'plot_params_to_file.py'),
    targetName='FlightDataPlotGenerator',
    excludes=opt.excludes + no_doc + no_gui + no_test + ['IPython', 'lib2to3', 'PIL'],
    includes=['matplotlib.backends.backend_wxagg'],
    packages=['scipy.integrate'],
)

FlightDataProcessing = Executable(
    script=lookup('flightdataprocessing', '__main__.py'),
    targetName='FlightDataProcessing',
    excludes=opt.excludes + no_api + no_doc + no_gui + no_test + ['compiler', 'Image', 'IPython', 'PIL', 'xml'],
)

FlightDataSignalFinder = Executable(
    script=lookup('flightdataplotgenerator', 'plot_words_to_file_autonomous.py'),
    targetName='FlightDataSignalFinder',
    excludes=opt.excludes + no_api + no_doc + no_gui + no_test + ['IPython', 'lib2to3', 'PIL'],
    includes=['matplotlib.backends.backend_wxagg', 'scipy.integrate.vode', 'scipy.integrate.lsoda'],
)

FlightDataVersion = Executable(
    script=lookup('utilities', 'polaris_version.py'),
    targetName='FlightDataVersion',
    excludes=opt.excludes + no_api + no_doc + no_gui + no_test + ['bz2', 'compiler', 'logging'],
)

FlightDataRunner = Executable(
    script=lookup('flightdatarunner', 'local_runner.py'),
    targetName='FlightDataRunner',
    excludes=opt.excludes + no_gui + no_test + ['IPython', 'osgeo', 'PIL'],
    includes=['lxml.etree', 'lxml._elementpath', 'matplotlib.backends.backend_wxagg', 'scipy.integrate', 'scipy.signal.sigtools'],
    packages=['analysis_engine', 'compass', 'data_exports', 'polarisconfiguration', 'data_validation', 'flightdataaircrafttables', 'flightdataprofiles', 'pkg_resources._vendor.packaging', 'scipy.integrate', 'scipy.signal'],
)

FlightDataHDFValidator = Executable(
    script=lookup('hdfaccess', 'tools', 'hdfvalidator.py'),
    targetName='FlightDataHDFValidator',
    excludes=opt.excludes + no_doc + no_gui + no_test + ['compiler', 'Image', 'IPython', 'PIL', 'xml'],
    packages=['analysis_engine'],
)

##############################################################################

# Defaults

# Prepare default build options for all editions:


#build_icon = 'FDS-icon-55x55x256.bmp'

executables = [
    FlightDataAnalyzer,
    FlightDataBitstreamAligner,
    FlightDataConverter,
    FlightDataParameterTree,
    FlightDataPlotter,
    FlightDataSplitter,
    LFLValidator,
    FlightDataHDFValidator,
]

include_files = [
    (lookup('analysis_engine', 'config'), 'config'),
    (lookup('flightdataparametertree', '_assets'), '_assets'),
    (lookup('flightdataparametertree', 'data'), 'data'),
    (lookup('flightdataparametertree', 'templates'), 'templates'),
    (lookup('geomag', 'WMM.COF'), os.path.join('geomag', 'WMM.COF')),
    (requests.certs.where(), 'cacert.pem'),
    #('icons', 'icons'),
    (os.path.join(os.path.dirname(lib2to3.__file__), 'Grammar.txt'), 'Grammar.txt'), # Fixes IOError: [Errno 2] No such file or directory: 'C:\\Program Files (x86)\\FlightDataServices\\POLARIS-Suite\\FlightDataRunner.exe\\lib2to3\\Grammar.txt'
    (os.path.join(os.path.dirname(opcode.__file__), 'distutils'), 'distutils'),
]

password = ''


##############################################################################

# Editions


# Handle special cases for different editions:

if opt.edition == 'Full':

    # Enable restricted features:
    FlightDataBitstreamAligner.script = lookup('filterpypefds', 'process_bitstream_file_plus.py')
    FlightDataAnalyzer.packages += ['data_validation', 'flightdataaircrafttables', 'flightdataprofiles']
    FlightDataSplitter.packages += ['data_validation']

    build_suffix = 'FE'

    password = 'open1eye'

    executables += [
        ConvertAGS, ConvertGRAF, FlightDataAligner, FlightDataCleanser,
        FlightDataConverter767, FlightDataPlotGenerator, FlightDataVersion,
        FlightDataReadoutValidator, FlightDataRunner, FlightDataSignalFinder,
        FlightDataProcessing,
    ]

    include_files += [
        (lookup('data_exports', 'resources'), 'exporter'),
        (lookup('data_validation', 'config_files'), 'config_files'),
        (lookup('flightdatadecompression', 'f1000', 'f1000.dll'), ''),
        (lookup('flightdatadecompression', 'fa2100', 'fa2100.dll'), ''),
        (lookup('flightdatarunner', 'default_settings-windows.yaml'), 'default_settings.yaml'),
        (lookup('flightdatarunner', 'resources'), 'resources'),
        (lookup('lflconversion', 'fds_lfl', 'data'), 'data'),
    ]

    for fn in opt.inject:
        path0 = os.path.join('custom_files', fn)
        path1 = lookup('analysis_engine', fn)
        try:
            shutil.copyfile(path0, path1)
        except:
            pass

elif opt.edition == 'Community':

    # Disable restricted features:
    FlightDataBitstreamAligner.excludes += protected
    FlightDataAnalyzer.excludes += protected
    FlightDataSplitter.excludes += protected

    build_suffix = 'CE'

    for fn in opt.inject:
        path0 = lookup('analysis_engine', fn)
        try:
            os.remove(path0)
        except:
            pass

elif opt.edition == 'Plotter':

    executables = [
        FlightDataPlotter, FlightDataPlotGenerator, FlightDataVersion,
        LFLValidator,
    ]

    #include_files = [
        ## (requests.certs.where(), 'cacert.pem'),
        #('icons', 'icons'),
    #]

    build_suffix = 'PE'

    for fn in opt.inject:
        path0 = lookup('analysis_engine', fn)
        try:
            os.remove(path0)
        except:
            pass

else:

    print('Oh dear, I don\'t know what edition to build. Exiting...')
    sys.exit(1)


##############################################################################
    
# Setup


# Remove the build and dist directories if they already exist:
for directory in ('build', 'dist'):
    if os.path.isdir(directory):
        shutil.rmtree(directory, ignore_errors=True)


# Pass through all of the options prepared above:
setup(
    name='POLARIS-Suite-%s' % build_suffix,
    version=opt.version,
    description='POLARIS-Suite %s Edition' % opt.edition,
    long_description='Copyright (c) Flight Data Services Ltd',
    author='Flight Data Services Ltd',
    options={
        'build_exe': {
            'excludes': opt.excludes,
            'include_files': include_files,
            #'include_msvcr': True,
            'optimize': 0,
            'compressed': opt.compress,
            'append_script_to_exe': True,
            'create_shared_zip': False,
            'include_in_shared_zip': False,
            'copy_dependent_files': True,
           # 'icon': 'icons/POLARIS.ico',
            'silent': True,
        },
        #'install_exe': {
            #'force': True,
        #},
        'bdist_dmg': {
            #'add_to_path': True,
            'bundle_name': 'POLARIS-Suite',
        },
    },
    executables=executables,
)


##############################################################################    

# Installer


#if opt.installer:

    ## Populate the substitutions used in the templates:
    #substitutions = {
        #'python_dir': opt.python_dir,
        #'build_dir': opt.build_dir,
        #'build_edition': opt.edition,
##        'build_icon': build_icon,
        #'build_suffix': build_suffix,
        #'password': password,
        #'version': opt.version,
    #}

    ## Make suite shell command prompt script from template:
    #tn = os.path.join('templates', '%s-Shell.template' % build_suffix)
    #sn = os.path.join(opt.build_dir, 'POLARIS-Shell.cmd')
    #with open(tn, 'r') as tf, open(sn, 'w') as sf:
        #template = string.Template(tf.read())
        #sf.write(template.substitute(substitutions))

    # Make suite installer generator script from template:
    #tn = os.path.join('templates', 'iss.template')
    #sn = '%s.iss' % build_suffix
    #with open(tn, 'r') as tf, open(sn, 'w') as sf:
        #template = string.Template(tf.read())
        #sf.write(template.substitute(substitutions))

    # Execute the installer building application:
    #iscc = os.path.join('C:\\', 'Program Files', 'Inno Setup 5', 'ISCC.exe')
    #if os.path.isfile(iscc):
        #subprocess.call([iscc, '%s.iss' % build_suffix])
    #os.remove(build_suffix + '.iss')
