import os
import hashlib
import zipfile
from xml.etree import ElementTree

SCRIPT_VERSION = 3
KODI_VERSIONS = ["omega", "repo"]
IGNORE = [".git", ".github", ".gitignore", ".DS_Store", "thumbs.db", ".idea", "venv"]

# Debugging: Initial Configuration
print(f"Script Version: {SCRIPT_VERSION}")
print(f"KODI_VERSIONS: {KODI_VERSIONS}")
print(f"IGNORE patterns: {IGNORE}")


def convert_bytes(num):
    """
    Converts bytes to human-readable units.
    """
    for x in ["bytes", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return f"{num:3.1f} {x}"
        num /= 1024.0


class Generator:
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
            print(f"Successfully updated {addons_xml_path}")  # DEBUG
            if self._generate_md5_file(addons_xml_path, md5_path):
                print(f"Successfully updated {md5_path}")  # DEBUG

    def _remove_binaries(self):
        print("Starting binary removal process...")  # DEBUG
        for parent, _, filenames in os.walk(self.release_path):
            print(f"Scanning directory: {parent}")  # DEBUG
            for fn in filenames:
                if fn.lower().endswith("pyo") or fn.lower().endswith("pyc"):
                    compiled = os.path.join(parent, fn)
                    try:
                        os.remove(compiled)
                        print(f"Removed compiled python file: {compiled}")  # DEBUG
                    except Exception as e:
                        print(f"Failed to remove compiled python file: {compiled}. Error: {e}")  # DEBUG

    def _create_zip(self, folder, addon_id, version):
        print(f"Attempting to create zip for addon: {addon_id}, version: {version}, folder: {folder}")  # DEBUG
        addon_folder = os.path.join(self.release_path, folder)
        zip_folder = os.path.join(self.zips_path, addon_id)
        if not os.path.exists(zip_folder):
            print(f"Creating zip folder at {zip_folder}")  # DEBUG
            os.makedirs(zip_folder)

        final_zip = os.path.join(zip_folder, f"{addon_id}-{version}.zip")
        print(f"Creating zip file: {final_zip}")  # DEBUG
        with zipfile.ZipFile(final_zip, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            root_len = len(os.path.dirname(os.path.abspath(addon_folder)))
            for root, dirs, files in os.walk(addon_folder):
                for i in IGNORE:
                    if i in dirs:
                        dirs.remove(i)
                archive_root = os.path.abspath(root)[root_len:]
                for f in files:
                    fullpath = os.path.join(root, f)
                    archive_name = os.path.join(archive_root, f)
                    zipf.write(fullpath, archive_name, zipfile.ZIP_DEFLATED)

        size = convert_bytes(os.path.getsize(final_zip))
        print(f"Zip created: {final_zip}, size: {size}")  # DEBUG

    def _generate_md5_file(self, addons_xml_path, md5_path):
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
        print("Generating addons.xml...")  # DEBUG
        if not os.path.exists(addons_xml_path):
            print(f"{addons_xml_path} does not exist. Creating a new addons.xml file.")  # DEBUG
            addons_root = ElementTree.Element("addons")
            addons_xml = ElementTree.ElementTree(addons_root)
        else:
            print(f"{addons_xml_path} found. Parsing existing addons.xml.")  # DEBUG
            addons_xml = ElementTree.parse(addons_xml_path)
            addons_root = addons_xml.getroot()

        folders = [
            i for i in os.listdir(self.release_path)
            if os.path.isdir(os.path.join(self.release_path, i))
            and i != "zips"
            and not i.startswith(".")
            and os.path.exists(os.path.join(self.release_path, i, "addon.xml"))
        ]
        print(f"Detected addon folders: {folders}")  # DEBUG

        addon_xpath = "addon[@id='{}']"
        changed = False
        for addon in folders:
            try:
                addon_xml_path = os.path.join(self.release_path, addon, "addon.xml")
                addon_xml_tree = ElementTree.parse(addon_xml_path)
                addon_root = addon_xml_tree.getroot()
                addon_id = addon_root.get("id")
                version = addon_root.get("version")
                print(f"Detected Addon ID: {addon_id}, Version: {version}")  # DEBUG

                # Update xbmc.python version if necessary
                for requires in addon_root.findall("requires"):
                    for import_tag in requires.findall("import"):
                        if import_tag.get("addon") == "xbmc.python" and import_tag.get("version") == "2.1.0":
                            print(f"Updating xbmc.python version from 2.1.0 to 3.0.0 for {addon_id}")  # DEBUG
                            import_tag.set("version", "3.0.0")

                # Check for existing entry and update if found
                existing_addon = addons_root.find(addon_xpath.format(addon_id))
                if existing_addon is not None:
                    print(f"Existing entry for {addon_id} found. Replacing it.")  # DEBUG
                    addons_root.remove(existing_addon)

                addons_root.append(addon_root)
                changed = True

            except Exception as e:
                print(f"Error processing addon {addon}: {e}")  # DEBUG

        if changed:
            try:
                addons_xml.write(addons_xml_path, encoding="utf-8", xml_declaration=True)
                print(f"addons.xml successfully written to {addons_xml_path}")  # DEBUG
                return True
            except Exception as e:
                print(f"Error writing to {addons_xml_path}: {e}")  # DEBUG
        else:
            print("No changes detected in addons.xml.")  # DEBUG
        return False


if __name__ == "__main__":
    for release in [r for r in KODI_VERSIONS if os.path.exists(r)]:
        Generator(release)
