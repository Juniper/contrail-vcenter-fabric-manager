# -*- mode: python; -*-

#
# Copyright (c) 2018 Juniper Networks, Inc. All rights reserved.
#
import os
import fnmatch

env = DefaultEnvironment()

setup_sources = [
    'setup.py',
    'requirements.txt',
]

setup_sources_rules = []
for file in setup_sources:
    setup_sources_rules.append(
        env.Install(Dir('.'), "#vcenter-fabric-manager/cvfm/" + file))

cvfm_sandesh_files = [
    'vcenter_fabric_manager.sandesh',
]

cvfm_sandesh = [
    env.SandeshGenPy(sandesh_file, 'cvfm/sandesh/', False)
    for sandesh_file in cvfm_sandesh_files
]

cvfm_source_files = [
    file_ for file_ in os.listdir(Dir('#vcenter-fabric-manager/cvfm/').abspath)
    if fnmatch.fnmatch(file_, '*.py')
]

cvfm = [
    env.Install(Dir('cvfm'), '#vcenter-fabric-manager/cvfm/' + cvfm_file)
    for cvfm_file in cvfm_source_files
]
cvfm.append(env.Install(Dir('.'), "#vcenter-fabric-manager/setup.py"))
cvfm.append(env.Install(Dir('.'), "#vcenter-fabric-manager/requirements.txt"))

env.Depends(cvfm, cvfm_sandesh, setup_sources_rules)
env.Alias('cvfm', cvfm)

install_cmd = env.Command(None, 'setup.py',
        'cd ' + Dir('.').path + ' && python setup.py install %s' % env['PYTHON_INSTALL_OPT'])

env.Depends(install_cmd, cvfm)
env.Alias('cvfm-install', install_cmd)
