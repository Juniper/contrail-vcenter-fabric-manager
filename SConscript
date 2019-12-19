# -*- mode: python; -*-

#
# Copyright (c) 2018 Juniper Networks, Inc. All rights reserved.
#
import itertools
import os
import fnmatch

env = DefaultEnvironment()

setup_sources = [
    'setup.py',
    'requirements.txt',
    'requirements_dev.txt',
    'tox.ini',
    '.coveragerc',
    'pyproject.toml'
]

setup_sources_rules = []
for file in setup_sources:
    setup_sources_rules.append(
        env.Install(Dir('.'), "#vcenter-fabric-manager/" + file))

cvfm_sandesh_files = ["vcenter_fabric_manager.sandesh"]

cvfm_sandesh = [
    env.SandeshGenPy(sandesh_file, "cvfm/sandesh/", False)
    for sandesh_file in cvfm_sandesh_files
]

cvfm_root_dir = Dir("#vcenter-fabric-manager/").abspath

cvfm_source_files = []
for root, dirs, files in os.walk(os.path.join(cvfm_root_dir, "cvfm")):
    for _file in files:
        if fnmatch.fnmatch(_file, "*.py"):
            abs_path = os.path.join(root, _file)
            if fnmatch.fnmatch(abs_path, "*/sandesh/*"):
                continue
            rel_path = os.path.relpath(abs_path, cvfm_root_dir)
            cvfm_source_files.append(rel_path)

cvfm_test_files = []
for root, dirs, files in os.walk(os.path.join(cvfm_root_dir, "tests")):
    for _file in files:
        if fnmatch.fnmatch(_file, "*.py") or fnmatch.fnmatch(_file, "*.conf"):
            abs_path = os.path.join(root, _file)
            rel_path = os.path.relpath(abs_path, cvfm_root_dir)
            cvfm_test_files.append(rel_path)


cvfm = []
for cvfm_file in itertools.chain(cvfm_source_files, cvfm_test_files):
    target = "/".join(cvfm_file.split("/")[:-1])
    cvfm.append(
        env.Install(Dir(target), "#vcenter-fabric-manager/" + cvfm_file)
    )

cd_cmd = 'cd ' + Dir('.').path + ' && '
sdist_depends = []
sdist_depends.extend(setup_sources_rules)
sdist_depends.extend(cvfm)
sdist_depends.extend(cvfm_sandesh)
sdist_gen = env.Command('dist/contrail-vcenter-fabric-manager-0.1dev.tar.gz',
                        'setup.py', cd_cmd + 'python setup.py sdist')

env.Depends(sdist_gen, sdist_depends)

test_target = env.SetupPyTestSuite(sdist_gen, use_tox=True)
env.Alias('vcenter-fabric-manager:test', test_target)

env.Depends(cvfm, cvfm_sandesh)
env.Alias("cvfm", cvfm)

install_cmd = env.Command(
    None,
    "setup.py",
    "cd "
    + Dir(".").path
    + " && python setup.py install %s" % env["PYTHON_INSTALL_OPT"],
)

env.Depends(install_cmd, cvfm)
env.Alias("cvfm-install", install_cmd)
