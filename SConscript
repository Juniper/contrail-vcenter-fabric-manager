# -*- mode: python; -*-

#
# Copyright (c) 2018 Juniper Networks, Inc. All rights reserved.
#
import os
import fnmatch

env = DefaultEnvironment()

cvfm_sandesh_files = [
    'vcenter_fabric_manager.sandesh',
]

cvfm_sandesh = [
    env.SandeshGenPy(sandesh_file, 'cvfm/sandesh/', False)
    for sandesh_file in cvfm_sandesh_files
]

cvfm_root_dir = Dir('#vcenter-fabric-manager/cvfm/').abspath
cvfm_source_dirs = [cvfm_root_dir] + [d for d in glob.glob(path + "**/") if not fnmatch.fnmatch(d, '*/sandesh/*')]

cvfm_source_files = [
f.replace(cvfm_root_dir, '') for f in glob.glob(d + '*.py') for d in dirs] + [
f.replace(cvfm_root_dir, '') for f in glob.glob(path + "*.py")
]

cvfm = [
    env.Install(Dir('cvfm'), '#vcenter-fabric-manager/cvfm/' + cvfm_file)
    for cvfm_file in cvfm_source_files
]
cvfm.append(env.Install(Dir('.'), "#vcenter-fabric-manager/setup.py"))
cvfm.append(env.Install(Dir('.'), "#vcenter-fabric-manager/requirements.txt"))

env.Depends(cvfm, cvfm_sandesh)
env.Alias('cvfm', cvfm)

install_cmd = env.Command(None, 'setup.py',
        'cd ' + Dir('.').path + ' && python setup.py install %s' % env['PYTHON_INSTALL_OPT'])

env.Depends(install_cmd, cvfm)
env.Alias('cvfm-install', install_cmd)
