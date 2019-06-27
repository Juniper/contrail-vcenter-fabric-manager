#!/usr/bin/env python
from __future__ import print_function
import os
import argparse
import yaml
import subprocess
from lxml import etree


def get_head_commit_sha(path):
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path)
    return sha[:-1]


def get_head_branch(path):
    """Return the git ref that is currently checked-out in the working copy
    at path"""
    head = subprocess.check_output(['git', 'symbolic-ref', 'HEAD'], cwd=path)
    return head[:-1]


def dump_xml(node):
    return etree.tostring(node, pretty_print=True).decode()


def del_node(node):
    node.getparent().remove(node)


def get_project(zuul_var, short_name):
    for project, data in zuul_var['_projects'].items():
        if data['short_name'] == short_name:
            return data
    msg = "Zuul does not know about project {}.\n".format(short_name)
    msg += "Make sure it is defined in ``required-projects'' for this job."
    raise RuntimeError(msg)


def get_remote_name_for_zuul_project(project):
    """This generates the names used in remote tags in the manifest.xml file
    Remote name is hostname+namespace"""
    namespace = os.path.split(project['name'])[0]
    remote_name = project['canonical_hostname']
    if namespace: # skip the join if namespace is empty
        remote_name = os.path.join(remote_name, namespace)
    return remote_name


def generate_remotes(zuul_var):
    """This function generates a dict of {remote_name: remote XML node}.
    The XML nodes will be later added to the manifest file.
    It also extends the projects in zuul dict to contain the remote name,
    for future matching against the remote nodes."""
    remotes = {}
    for name, project in zuul_var['_projects'].items():
        remote_name = get_remote_name_for_zuul_project(project)
        project['remote_name'] = remote_name
        remotes[remote_name] = etree.Element(
            'remote',
            name=remote_name,
            fetch='file://' + os.path.join(
                zuul_var['executor']['src_root'],
                remote_name))
        remotes[remote_name].tail = '\n'
    return remotes


def translate(args):
    """This will rewrite manifest to fetch repositories from filesystem locations
    instead of GitHub URLs. This way zuul-merger-prepared checkouts can be used
    during `repo sync`
    """
    with open(args.zuul_vars_path, 'r') as zuul_var_file:
        zuul_var = yaml.load(zuul_var_file)

    with open(args.source_manifest_path, 'r') as manifest_file:
        manifest = etree.parse(manifest_file)

    for remote in manifest.xpath('//remote'):
        del_node(remote)

    for default in manifest.xpath('//default'):
        del_node(default)

    remotes = generate_remotes(zuul_var)

    for remote in remotes.values():
        manifest.getroot().insert(0, remote)

    for project in manifest.xpath('//project'):
        name = project.attrib['name']
        zuul_project = get_project(zuul_var, name)
        project.attrib['remote'] = zuul_project['remote_name']
        head = get_head_branch(
            zuul_var['executor']['work_root'] +
            '/' + zuul_project['src_dir'])
        project.attrib['revision'] = head

    return manifest


def snapshot(args):
    """ This will rewrite manifest by adding git commit SHAs to each project
    in the "revision" attribute. This is for preserving the information about
    the exact code version used during the build
    """
    with open(args.source_manifest_path, 'r') as manifest_file:
        manifest = etree.parse(manifest_file)
    with open(args.zuul_vars_path, 'r') as zuul_var_file:
        zuul_var = yaml.load(zuul_var_file)
    for project in manifest.xpath('//project'):
        name = project.attrib['name']
        zuul_project = get_project(zuul_var, name)
        sha = get_head_commit_sha(
            zuul_var['executor']['work_root'] +
            '/' + zuul_project['src_dir'])
        project.attrib['revision'] = sha
    return manifest


def checkout(args):
    """This is a function used for testing: it will simulate a zuul-merger
    checkout layout based on information from a manifest file
    """
    with open(args.source_manifest_path, 'r') as manifest_file:
        manifest = etree.parse(manifest_file)
    with open(args.zuul_vars_path, 'r') as zuul_var_file:
        zuul_var = yaml.load(zuul_var_file)
    for project in manifest.xpath('//project'):
        name = project.attrib['name']
        zuul_project = get_project(zuul_var, name)
        url = 'https://' + zuul_project['canonical_name']
        path = zuul_project['src_dir']
        command = ['git', 'clone', url, path]
        print(command)
        subprocess.check_output(command)
    return manifest


def main():
    actions = {
        "translate": translate,
        "snapshot": snapshot,
        "checkout": checkout
    }

    parser = argparse.ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("zuul_vars_path")
    parser.add_argument("source_manifest_path")
    parser.add_argument("target_manifest_path", nargs="?")
    args = parser.parse_args()
    # overwrite source if separate target not provided
    args.target_manifest_path = (args.target_manifest_path or
                                 args.source_manifest_path)

    manifest = actions[args.action](args)
    output = dump_xml(manifest)
    with open(args.target_manifest_path, 'w') as manifest_file:
        manifest_file.write(output)


if __name__ == "__main__":
    main()
