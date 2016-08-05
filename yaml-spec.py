import yaml
import copy
from argparse import ArgumentParser

argparser = ArgumentParser()
argparser.add_argument("file")
args = argparser.parse_args()

input_file = args.file

with open(input_file, "r") as fd:
    yaml_spec = yaml.safe_load(fd)

# Use pop here to leave out the custom vars we'll define later on
language = yaml_spec.pop("language")

if language != "python":
    raise NotImplementedError("PYTHON ONLY")

version = yaml_spec.pop("version")
release = yaml_spec.pop("release")
summary = yaml_spec.pop("summary")
license = yaml_spec.pop("license")
sources = yaml_spec.pop("sources")
architechtures = yaml_spec.pop("architechtures")
description = yaml_spec.pop("description")
python_versions = yaml_spec.pop("python-versions")
python_setup = yaml_spec.pop("python-setup")
python_check = yaml_spec.pop("python-check")
changelog_from_git = yaml_spec.pop("changelog-from-git")
files = yaml_spec.pop("files")

# Optional params
name = yaml_spec.pop("name", None)
egginfoname = yaml_spec.pop("egginfoname", None)
patches = yaml_spec.pop("patches", [])

# Other vars are variables
spec_vars = copy.deepcopy(yaml_spec)

# ----------------
# Add some magic for vars

if 'modulename' in spec_vars.keys():
    module_name = spec_vars['modulename']

if not egginfoname:
    egginfoname = module_name

if not name:
    name = "python-%{modulename}"
    name_expanded = "python-{}".format(module_name)
else:
    name_expanded = name

# FIXME: this should be done for fedora only
release = "{}%{{?dist}}".format(release)

url = "https://pypi.python.org/pypi/{}".format(spec_vars['modulename'])

build_arch = None
if isinstance(architechtures, list):
    build_arch = ' '.join(architechtures)

build_requires_list = []

if python_setup == 'setuptools':
    build_requires_list.append("python{}-setup")

# -------------
# build the spec

spec = []

for var_name, var_value in spec_vars.items():
    spec.append("%global {0} {1}".format(var_name, var_value))

spec.append('')

spec.append("Name: {}".format(name))
spec.append("Version: {}".format(version))
spec.append("Release: {}".format(release))
spec.append("Summary: {}".format(summary))
spec.append('')

spec.append("License: {}".format(license))
spec.append("URL: {}".format(url))

for i, source in enumerate(sources):
    spec.append("Source{}: {}".format(i, source))

for i, patch in enumerate(patches):
    spec.append("Patch{}: {}".format(i, patch))

spec.append('')

if build_arch:
    spec.append("BuildArch: {}".format(build_arch))
    spec.append('')

spec.append("Description: {}".format(description))
spec.append('')

for v in python_versions:
    build_requires = ["python{}-devel"]
    build_requires = build_requires + build_requires_list
    build_requires = [br.format(v) for br in build_requires]

    spec.append("%package -n python{}-%{{modulename}}".format(v))
    spec.append("Summary: {}".format(description.strip()))
    python_provide = "python{}-%{{modulename}}".format(v)
    spec.append("%%{?python_provide:%%python_provide %s}" % python_provide)

    for br in build_requires:
        spec.append("BuildRequires: {}".format(br))

    spec.append('')

    spec.append("%description -n python{0}-%{{modulename}} {1}".format(v, description))
    spec.append("Python {} version".format(v))
    spec.append("")

spec.append("%prep")
spec.append("%autosetup -n {}-%{{version}}".format(module_name))
spec.append("")

spec.append("%build")
for v in python_versions:
    spec.append("%py{}_build".format(v))
spec.append("")

spec.append("%install")
for v in python_versions:
    spec.append("%py{}_install".format(v))
spec.append("")

spec.append("%check")
for v in python_versions:
    python_bin = "%%{__python%s}" % v
    if python_check == "setup_py_test":
        spec.append("{} setup.py test".format(python_bin))
    elif python_check == "nose":
        spec.append("{} -m nose".format(python_bin))
    elif python_check == "pytest":
        spec.append("{} -m py.test".format(python_bin))
spec.append("")

for v in python_versions:
    spec.append("%files -n python{0}-%{{modulename}}".format(v))
    spec.append("%license {}".format(' '.join(files.get('license', []))))
    spec.append("%doc {}".format(' '.join(files.get('docs', []))))
    if files.get('other', []):
        spec.append(' '.join(files.get('other', [])))

    sitelib = "%%{python%s_sitelib}" % v
    spec.append('{0}/{1}-*.egg-info/'.format(sitelib, egginfoname))
    spec.append('{}/%{{modulename}}.py*'.format(sitelib))

    if v == 3:
        spec.append('{}/__pycache__/%{{modulename}}.*'.format(sitelib))

    spec.append('')

if changelog_from_git:
    spec.append("%changelog")
    spec.append("* Thu May 05 2016 Igor Gnatenko <ignatenko@redhat.com> - 1.3.3-1")
    spec.append("- Initial package")


# ----
# write the spec

spec_filename = "{}.spec".format(name_expanded)
with open(spec_filename, "w") as fd:
    fd.write('\n'.join(spec))

print("Spec written to {}".format(spec_filename))
