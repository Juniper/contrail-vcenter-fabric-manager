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

cvfm_sources_rules = [
    env.Install(Dir('cvfm'), '#vcenter-fabric-manager/cvfm/' + cvfm_file)
    for cvfm_file in cvfm_source_files
]

cd_cmd = 'cd ' + Dir('.').path + ' && '
sdist_depends = []
sdist_depends.extend(setup_sources_rules)
sdist_depends.extend(local_sources_rules)
sdist_depends.extend(sandesh_sources)
sdist_gen = env.Command('dist/vcenter_fabric_manager-0.1dev.tar.gz', 'setup.py',
                        cd_cmd + 'python setup.py sdist')

env.Depends(sdist_gen, sdist_depends)
env.Default(sdist_gen)

install_cmd = env.Command(None, 'setup.py',
        'cd ' + Dir('.').path + ' && python setup.py install %s' % env['PYTHON_INSTALL_OPT'])

env.Depends(install_cmd, sdist_depends)
env.Alias('cvfm-install', install_cmd)
