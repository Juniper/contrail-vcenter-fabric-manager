# -*- mode: python; -*-

#
# Copyright (c) 2018 Juniper Networks, Inc. All rights reserved.
#
import os
import fnmatch

env = DefaultEnvironment()

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

cvfm = []
for cvfm_file in cvfm_source_files:
    target = "/".join(cvfm_file.split("/")[:-1])
    cvfm.append(
        env.Install(Dir(target), "#vcenter-fabric-manager/" + cvfm_file)
    )

cvfm = [
    env.Install(Dir("cvfm"), "#vcenter-fabric-manager/" + cvfm_file)
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
