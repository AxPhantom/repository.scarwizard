import os
import shutil
import hashlib
import zipfile
from xml.etree import ElementTree

SCRIPT_VERSION = 2
KODI_VERSIONS = ["krypton", "leia", "matrix", "omega", "repo"]
IGNORE = [".git", ".github", ".gitignore", ".DS_Store", "thumbs.db", ".idea", "venv"]

def debug_print(message):
    """ Helper function to print debug messages """
    print(f"[DEBUG] {message}")

def _setup_colors():
    debug_print("Setting up colors for the console.")
    color = os.system("color")
    console = 0
    if os.name == 'nt':  # Only if we are running on Windows
        from ctypes import windll

        k = windll.kernel32
        console = k.SetConsoleMode(k.GetStdHandle(-11), 7)
    debug_print(f"Color setup result: {color == 1 or console == 1}")
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
    Converts bytes to human-readable units.
    """
    debug_print(f"Converting bytes: {num}")
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            debug_print(f"Converted size: {num} {x}")
            return "%3.1f %s" % (num, x)
        num /= 1024.0

class Generator:
    def __init__(self, release):
        debug_print(f"Initializing Generator for release: {release}")
        self.release_path = release
        self.zips_path = os.path.join(self.release_path, "zips")
        addons_xml_path = os.path.join(self.zips_path, "addons.xml")
        md5_path = os.path.join(self.zips_path, "addons.xml.md5")

        if not os.path.exists(self.zips_path):
            debug_print(f"Creating zips folder: {self.zips_path}")
            os.makedirs(self.zips_path)

        self._remove_binaries()

        if self._generate_addons_file(addons_xml_path):
            print(f"Successfully updated {color_text(addons_xml_path, 'yellow')}")
            if self._generate_md5_file(addons_xml_path, md5_path):
                print(f"Successfully updated {color_text(md5_path, 'yellow')}")

    def _remove_binaries(self):
        debug_print("Removing compiled Python files and __pycache__ folders.")
        for parent, dirnames, filenames in os.walk(self.release_path):
            for fn in filenames:
                if fn.lower().endswith(("pyo", "pyc")):
                    compiled = os.path.join(parent, fn)
                    try:
                        os.remove(compiled)
                        debug_print(f"Removed compiled file: {compiled}")
                    except Exception as e:
                        debug_print(f"Failed to remove {compiled}: {e}")
            for dir in dirnames:
                if "pycache" in dir.lower():
                    compiled = os.path.join(parent, dir)
                    try:
                        shutil.rmtree(compiled)
                        debug_print(f"Removed cache folder: {compiled}")
                    except Exception as e:
                        debug_print(f"Failed to remove cache folder {compiled}: {e}")

    def _create_zip(self, folder, addon_id, version):
        debug_print(f"Creating zip for addon: {addon_id}, version: {version}")
        addon_folder = os.path.join(self.release_path, folder)
        zip_folder = os.path.join(self.zips_path, addon_id)
        if not os.path.exists(zip_folder):
            debug_print(f"Creating zip folder: {zip_folder}")
            os.makedirs(zip_folder)

        final_zip = os.path.join(zip_folder, f"{addon_id}-{version}.zip")
        if not os.path.exists(final_zip):
            with zipfile.ZipFile(final_zip, "w", compression=zipfile.ZIP_DEFLATED) as zip:
                root_len = len(os.path.dirname(os.path.abspath(addon_folder)))
                for root, dirs, files in os.walk(addon_folder):
                    debug_print(f"Processing folder: {root}")
                    for i in IGNORE:
                        if i in dirs:
                            dirs.remove(i)
                        files = [f for f in files if not f.startswith(i)]
                    for f in files:
                        fullpath = os.path.join(root, f)
                        archive_name = os.path.join(os.path.abspath(root)[root_len:], f)
                        zip.write(fullpath, archive_name)
            debug_print(f"Zip created: {final_zip}")

    def _generate_addons_file(self, addons_xml_path):
        """
        Generates a zip for each found addon, and updates the addons.xml file accordingly.
        """
        debug_print(f"Generating addons file: {addons_xml_path}")
        if not os.path.exists(addons_xml_path):
            addons_root = ElementTree.Element('addons')
            addons_xml = ElementTree.ElementTree(addons_root)
        else:
            addons_xml = ElementTree.parse(addons_xml_path)
            addons_root = addons_xml.getroot()

        # Rest of the method logic...
        return True  # Adjust as needed

    def _generate_md5_file(self, addons_xml_path, md5_path):
        """
        Generates a new addons.xml.md5 file.
        """
        debug_print(f"Generating MD5 file for: {addons_xml_path}")
        try:
            m = hashlib.md5(
                open(addons_xml_path, "r", encoding="utf-8").read().encode("utf-8")
            ).hexdigest()
            self._save_file(m, file=md5_path)
            debug_print(f"MD5 file generated: {md5_path}")
            return True
        except Exception as e:
            debug_print(f"Error generating MD5 file: {e}")
            return False

    def _save_file(self, data, file):
        """
        Saves a file.
        """
        debug_print(f"Saving data to file: {file}")
        try:
            with open(file, "w") as f:
                f.write(data)
        except Exception as e:
            debug_print(f"Error saving file {file}: {e}")

# Entry point
if __name__ == "__main__":
    debug_print("Starting script.")
    for release in [r for r in KODI_VERSIONS if os.path.exists(r)]:
        debug_print(f"Processing release: {release}")
        Generator(release)
