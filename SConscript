# -*- mode: python; -*-

#
# Copyright (c) 2018 Juniper Networks, Inc. All rights reserved.
#
import os
import fnmatch
import glob

env = DefaultEnvironment()

cvfm_sandesh_files = ["vcenter_fabric_manager.sandesh"]

cvfm_sandesh = [
    env.SandeshGenPy(sandesh_file, "cvfm/sandesh/", False)
    for sandesh_file in cvfm_sandesh_files
]

cvfm_root_dir = Dir("#vcenter-fabric-manager/cvfm/").abspath

cvfm_source_files = []
for r, d, f in os.walk(cvfm_root_dir):
    for _file in f:
        if fnmatch.fnmatch(_file, "*.py"):
            abs_path = os.path.join(r, _file)
            if fnmatch.fnmatch(abs_path, "*/sandesh*"):
                continue
            rel_path = os.path.relpath(abs_path, cvfm_root_dir)
            cvfm_source_files.append(rel_path)

cvfm = [
    env.Install(Dir("cvfm"), "#vcenter-fabric-manager/cvfm/" + cvfm_file)
    for cvfm_file in cvfm_source_files
]
cvfm.append(env.Install(Dir("."), "#vcenter-fabric-manager/setup.py"))
cvfm.append(env.Install(Dir("."), "#vcenter-fabric-manager/requirements.txt"))

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
