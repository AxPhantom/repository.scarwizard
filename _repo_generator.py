"""
Put this script in the root folder of your repo, and it will
zip up all addon folders, create a new zip in your zips folder,
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


def _setup_colors():
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
    Converts bytes to a human-readable format (KB, MB, etc.).
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


class Generator:
    """
    Generates a new addons.xml file from each addon's addon.xml file
    and a new addons.xml.md5 hash file. Must be run from the root of
    the checked-out repo.
    """

    def __init__(self, release):
        self.release_path = release
        self.zips_path = os.path.join(self.release_path, "zips")
        addons_xml_path = os.path.join(self.zips_path, "addons.xml")
        md5_path = os.path.join(self.zips_path, "addons.xml.md5")

        if not os.path.exists(self.zips_path):
            os.makedirs(self.zips_path)

        self._remove_binaries()

        if self._generate_addons_file(addons_xml_path):
            print(
                "Successfully updated {}".format(color_text(addons_xml_path, 'yellow'))
            )

            if self._generate_md5_file(addons_xml_path, md5_path):
                print("Successfully updated {}".format(color_text(md5_path, 'yellow')))

    def _remove_binaries(self):
        """
        Removes any and all compiled Python files before operations.
        """
        for parent, dirnames, filenames in os.walk(self.release_path):
            for fn in filenames:
                if fn.lower().endswith(("pyo", "pyc")):
                    compiled = os.path.join(parent, fn)
                    try:
                        os.remove(compiled)
                        print(
                            "Removed compiled python file: {}".format(
                                color_text(compiled, 'green')
                            )
                        )
                    except Exception as e:
                        print(
                            "Failed to remove compiled python file: {} ({})".format(
                                color_text(compiled, 'red'), e
                            )
                        )
            for dir in dirnames:
                if "pycache" in dir.lower():
                    compiled = os.path.join(parent, dir)
                    try:
                        shutil.rmtree(compiled)
                        print(
                            "Removed __pycache__ cache folder: {}".format(
                                color_text(compiled, 'green')
                            )
                        )
                    except Exception as e:
                        print(
                            "Failed to remove __pycache__ cache folder: {} ({})".format(
                                color_text(compiled, 'red'), e
                            )
                        )

    def _create_zip(self, folder, addon_id, version):
        """
        Creates a zip file in the zips directory for the given addon.
        """
        addon_folder = os.path.join(self.release_path, folder)
        zip_folder = os.path.join(self.zips_path, addon_id)
        if not os.path.exists(zip_folder):
            os.makedirs(zip_folder)

        final_zip = os.path.join(zip_folder, f"{addon_id}-{version}.zip")
        if not os.path.exists(final_zip):
            with zipfile.ZipFile(final_zip, "w", compression=zipfile.ZIP_DEFLATED) as zip:
                root_len = len(os.path.dirname(os.path.abspath(addon_folder)))

                for root, dirs, files in os.walk(addon_folder):
                    for i in IGNORE:
                        if i in dirs:
                            dirs.remove(i)
                        files = [f for f in files if not f.startswith(i)]

                    archive_root = os.path.abspath(root)[root_len:]

                    for f in files:
                        fullpath = os.path.join(root, f)
                        archive_name = os.path.join(archive_root, f)
                        zip.write(fullpath, archive_name)

            size = convert_bytes(os.path.getsize(final_zip))
            print(
                "Zip created for {} ({}) - {}".format(
                    color_text(addon_id, 'cyan'),
                    color_text(version, 'green'),
                    color_text(size, 'yellow'),
                )
            )

    def _generate_addons_file(self, addons_xml_path):
        """
        Generates a zip for each found addon and updates the addons.xml file accordingly.
        """
        addons_root = ElementTree.Element("root")

        folders = [
            i
            for i in os.listdir(self.release_path)
            if os.path.isdir(os.path.join(self.release_path, i))
            and i != "zips"
            and not i.startswith(".")
            and os.path.exists(os.path.join(self.release_path, i, "addon.xml"))
        ]

        changed = False
        for addon in folders:
            try:
                addon_xml_path = os.path.join(self.release_path, addon, "addon.xml")
                addon_xml = ElementTree.parse(addon_xml_path)
                addon_root = addon_xml.getroot()
                addon_id = addon_root.get("id")
                version = addon_root.get("version")

                addons_root.append(addon_root)
                self._create_zip(addon, addon_id, version)
                changed = True

            except Exception as e:
                print(
                    f"Excluding {addon}: {color_text(e, 'red')}"
                )

        if changed:
            addons_root[:] = sorted(
                addons_root, key=lambda addon: addon.get("id") or ""
            )
            try:
                ElementTree.ElementTree(addons_root).write(
                    addons_xml_path, encoding="utf-8", xml_declaration=True
                )
                return True
            except Exception as e:
                print(
                    "An error occurred updating {}!\n{}".format(
                        color_text(addons_xml_path, 'yellow'), color_text(e, 'red')
                    )
                )

    def _generate_md5_file(self, addons_xml_path, md5_path):
        """
        Generates a new addons.xml.md5 file.
        """
        try:
            with open(addons_xml_path, "r", encoding="utf-8") as f:
                md5_hash = hashlib.md5(f.read().encode("utf-8")).hexdigest()

            with open(md5_path, "w", encoding="utf-8") as f:
                f.write(md5_hash)

            return True
        except Exception as e:
            print(
                "An error occurred updating {}!\n{}".format(
                    color_text(md5_path, 'yellow'), color_text(e, 'red')
                )
            )


if __name__ == "__main__":
    for release in [r for r in KODI_VERSIONS if os.path.exists(r)]:
        Generator(release)
