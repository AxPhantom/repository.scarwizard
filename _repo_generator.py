"""
Put this script in the root folder of your repo and it will
zip up all addon folders, create a new zip in your zips folder
and then update the md5 and addons.xml file.
"""

import os
import shutil
import hashlib
import zipfile
from xml.etree import ElementTree

SCRIPT_VERSION = 2
KODI_VERSIONS = ["krypton", "leia", "matrix", "omega", "repo"]
IGNORE = [
    ".git",
    ".github",
    ".gitignore",
    ".DS_Store",
    "thumbs.db",
    ".idea",
    "venv",
]

# Debugging: Initial Configuration
print(f"Script Version: {SCRIPT_VERSION}")
print(f"KODI_VERSIONS: {KODI_VERSIONS}")
print(f"IGNORE patterns: {IGNORE}")

def _setup_colors():
    print("Setting up colors...")  # DEBUG
    color = os.system("color")
    console = 0
    if os.name == 'nt':  # Only if we are running on Windows
        from ctypes import windll

        k = windll.kernel32
        console = k.SetConsoleMode(k.GetStdHandle(-11), 7)
    return color == 1 or console == 1

_COLOR_ESCAPE = "\x1b[{}m"
_COLORS = {
    "black": "30",
    "red": "31",
    "green": "4;32",
    "yellow": "3;33",
    "blue": "34",
    "magenta": "35",
    "cyan": "1;36",
    "grey": "37",
    "endc": "0",
}
_SUPPORTS_COLOR = _setup_colors()

def color_text(text, color):
    return (
        '{}{}{}'.format(
            _COLOR_ESCAPE.format(_COLORS[color]),
            text,
            _COLOR_ESCAPE.format(_COLORS["endc"]),
        )
        if _SUPPORTS_COLOR
        else text
    )

def convert_bytes(num):
    """
    This function will convert bytes to MB.... GB... etc
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0

class Generator:
    """
    Generates a new addons.xml file from each addons addon.xml file
    and a new addons.xml.md5 hash file. Must be run from the root of
    the checked-out repo.
    """

    def __init__(self, release):
        print(f"Initializing Generator for release: {release}")  # DEBUG
        self.release_path = release
        self.zips_path = os.path.join(self.release_path, "zips")
        addons_xml_path = os.path.join(self.zips_path, "addons.xml")
        md5_path = os.path.join(self.zips_path, "addons.xml.md5")

        if not os.path.exists(self.zips_path):
            print(f"Creating zips directory at {self.zips_path}")  # DEBUG
            os.makedirs(self.zips_path)

        self._remove_binaries()

        if self._generate_addons_file(addons_xml_path):
            print(f"Successfully updated {color_text(addons_xml_path, 'yellow')}")  # DEBUG
            if self._generate_md5_file(addons_xml_path, md5_path):
                print(f"Successfully updated {color_text(md5_path, 'yellow')}")  # DEBUG

    def _remove_binaries(self):
        """
        Removes any and all compiled Python files before operations.
        """
        print("Starting binary removal process...")  # DEBUG
        for parent, dirnames, filenames in os.walk(self.release_path):
            print(f"Scanning directory: {parent}")  # DEBUG
            for fn in filenames:
                if fn.lower().endswith("pyo") or fn.lower().endswith("pyc"):
                    compiled = os.path.join(parent, fn)
                    try:
                        os.remove(compiled)
                        print(f"Removed compiled python file: {compiled}")  # DEBUG
                    except Exception as e:
                        print(f"Failed to remove compiled python file: {compiled}. Error: {e}")  # DEBUG
            for dir in dirnames:
                if "pycache" in dir.lower():
                    compiled = os.path.join(parent, dir)
                    try:
                        shutil.rmtree(compiled)
                        print(f"Removed __pycache__ cache folder: {compiled}")  # DEBUG
                    except Exception as e:
                        print(f"Failed to remove __pycache__ cache folder: {compiled}. Error: {e}")  # DEBUG

    def _create_zip(self, folder, addon_id, version):
        """
        Creates a zip file in the zips directory for the given addon.
        """
        print(f"Attempting to create zip for addon: {addon_id}, version: {version}, folder: {folder}")  # DEBUG
        addon_folder = os.path.join(self.release_path, folder)
        zip_folder = os.path.join(self.zips_path, addon_id)
        if not os.path.exists(zip_folder):
            print(f"Creating zip folder at {zip_folder}")  # DEBUG
            os.makedirs(zip_folder)

        final_zip = os.path.join(zip_folder, f"{addon_id}-{version}.zip")
        print(f"Creating zip file: {final_zip}")  # DEBUG
        zip = zipfile.ZipFile(final_zip, "w", compression=zipfile.ZIP_DEFLATED)
        root_len = len(os.path.dirname(os.path.abspath(addon_folder)))

        for root, dirs, files in os.walk(addon_folder):
            print(f"Adding files from {root}")  # DEBUG
            for i in IGNORE:
                if i in dirs:
                    dirs.remove(i)

            archive_root = os.path.abspath(root)[root_len:]
            for f in files:
                fullpath = os.path.join(root, f)
                archive_name = os.path.join(archive_root, f)
                zip.write(fullpath, archive_name, zipfile.ZIP_DEFLATED)

        zip.close()
        size = convert_bytes(os.path.getsize(final_zip))
        print(f"Zip created: {final_zip}, size: {size}")  # DEBUG

    def _copy_meta_files(self, addon_id, addon_folder):
        """
        Copy the addon.xml and relevant art files into the relevant folders in the repository.
        """
        print(f"Copying metadata files for addon: {addon_id}")  # DEBUG
        try:
            addon_xml_path = os.path.join(self.release_path, addon_id, "addon.xml")
            tree = ElementTree.parse(addon_xml_path)
            root = tree.getroot()

            copy_files = ["addon.xml"]
            for ext in root.findall("extension"):
                if ext.get("point") in ["xbmc.addon.metadata", "kodi.addon.metadata"]:
                    assets = ext.find("assets")
                    if not assets:
                        continue
                    for art in [a for a in assets if a.text]:
                        copy_files.append(os.path.normpath(art.text))

            src_folder = os.path.join(self.release_path, addon_id)
            for file in copy_files:
                src_path = os.path.join(src_folder, file)
                if not os.path.exists(src_path):
                    print(f"Metadata file {file} not found for addon {addon_id}")  # DEBUG
                    continue

                dest_path = os.path.join(addon_folder, file)
                dest_folder = os.path.dirname(dest_path)
                if not os.path.exists(dest_folder):
                    os.makedirs(dest_folder)
                shutil.copy(src_path, dest_path)
                print(f"Copied {file} to {dest_path}")  # DEBUG
        except Exception as e:
            print(f"Error copying metadata files for addon {addon_id}: {e}")  # DEBUG

    def _generate_md5_file(self, addons_xml_path, md5_path):
        """
        Generates a new addons.xml.md5 file.
        """
        print(f"Generating MD5 checksum for {addons_xml_path}")  # DEBUG
        try:
            with open(addons_xml_path, "r", encoding="utf-8") as f:
                md5_hash = hashlib.md5(f.read().encode("utf-8")).hexdigest()
            with open(md5_path, "w", encoding="utf-8") as f:
                f.write(md5_hash)
            print(f"MD5 file created: {md5_path}")  # DEBUG
            return True
        except Exception as e:
            print(f"Error generating MD5 file for {addons_xml_path}: {e}")  # DEBUG
            return False

    def _generate_addons_file(self, addons_xml_path):
        """
        Generates a zip for each found addon, and updates the addons.xml file accordingly.
        """
        print("Generating addons.xml...")  # DEBUG
        if not os.path.exists(addons_xml_path):
            print(f"{addons_xml_path} does not exist. Creating a new addons.xml file.")  # DEBUG
            addons_root = ElementTree.Element('addons')  # Initialize root element
            addons_xml = ElementTree.ElementTree(addons_root)
        else:
            print(f"{addons_xml_path} found. Parsing existing addons.xml.")  # DEBUG
            addons_xml = ElementTree.parse(addons_xml_path)
            addons_root = addons_xml.getroot()

        folders = [
            i
            for i in os.listdir(self.release_path)
            if os.path.isdir(os.path.join(self.release_path, i))
            and i != "zips"
            and not i.startswith(".")
            and os.path.exists(os.path.join(self.release_path, i, "addon.xml"))
        ]
        print(f"Detected addon folders: {folders}")  # DEBUG

        addon_xpath = "addon[@id='{}']"
        changed = False
        for addon in folders:
            print(f"Processing addon folder: {addon}")  # DEBUG
            try:
                addon_xml_path = os.path.join(self.release_path, addon, "addon.xml")
                addon_xml_tree = ElementTree.parse(addon_xml_path)
                addon_root = addon_xml_tree.getroot()
                id = addon_root.get('id')
                version = addon_root.get('version')
                print(f"Detected Addon ID: {id}, Version: {version}")  # DEBUG

                print(f"Forcing update for {id}. Recreating zip and updating addons.xml.")  # DEBUG
                updated = True
                changed = True
                self._create_zip(addon, id, version)
                self._copy_meta_files(addon, os.path.join(self.zips_path, id))

                addons_root.append(addon_root)  # Always append or replace the addon entry

            except Exception as e:
                print(f"Error processing addon {addon}: {e}")  # DEBUG

        if changed:
            try:
                print(f"Writing addons.xml to {addons_xml_path}")  # DEBUG
                addons_xml.write(addons_xml_path, encoding="utf-8", xml_declaration=True)
                return changed
            except Exception as e:
                print(f"Error writing to {addons_xml_path}: {e}")  # DEBUG
        else:
            print("No changes detected in addons.xml")  # DEBUG

if __name__ == "__main__":
    for release in [r for r in KODI_VERSIONS if os.path.exists(r)]:
        generator = Generator(release)
