#!/usr/bin/env python
"""AckAck acknowledgements generator."""

from argparse import ArgumentParser
import codecs
import os
import plistlib
import re
import sys

VERSION = '2.0'


def main():
    """Main entry point of application."""

    # Process input arguments
    parser = ArgumentParser(
        description="AckAck " + VERSION + " - Acknowledgements Plist Generator"
                    "Generates a Settings.plist for iOS based on your Carthage or CocoaPods frameworks."
                    "Visit https://github.com/Building42/AckAck for more information.",
        epilog="If you run without any options, it will try to find the folders for you. "
               "This usually works fine if the script is in the project root or in a Scripts subfolder."
    )
    parser.add_argument(
        "--version", "-v",
        help="dispays the version information",
        action="store_true"
    )
    parser.add_argument(
        "--quiet", "-q",
        help="do not generate any output unless there are errors",
        action="store_true"
    )
    parser.add_argument(
        "--input", "-i",
        help="manually provide the path to the input folder(s), e.g. Carthage/Checkouts",
        nargs='+'
    )
    parser.add_argument(
        "--output", "-o",
        help="manually provide the path to the output folder, e.g. MyProject/Settings.bundle"
    )
    parser.add_argument(
        "--no-clean", "-n",
        help="do not remove existing license plists",
        action="store_true"
    )
    parser.add_argument(
        "--max-depth", "-d",
        help="specify the maximum folder depth to look for licenses",
        type=int
    )

    args = parser.parse_args()

    # Arguments
    input_folders = None
    output_folder = None
    max_depth = 1
    clean_up = True
    quiet = False

    if args.version:
        print 'AckAck ' + VERSION
        sys.exit()

    if args.quiet:
        quiet = True

    if args.input:
        input_folders = args.input

    if args.output:
        output_folder = args.output

    if args.max_depth:
        max_depth = args.max_depth

    if args.no_clean:
        clean_up = False

    # No input folder(s)? Find them
    if not input_folders:
        input_folders = find_input_folders(quiet)

    # No output folder? Find it
    if not output_folder:
        output_folder = find_output_folder(quiet)

    # Generate the acknowledgements
    generate(input_folders, output_folder, max_depth, clean_up, quiet)


def find_input_folders(quiet):
    """Finds the input folder based on the location of the Carthage folder."""

    # Find the Carthage Checkouts folder
    carthage_folder = find_folder(os.getcwd(), 'Carthage/Checkouts')

    # Look for the CocoaPods Pods folder
    cocoapods_folder = find_folder(os.getcwd(), 'Pods')

    input_folders = []
    if carthage_folder and os.path.isdir(carthage_folder):
        input_folders.append(carthage_folder)
    if cocoapods_folder and os.path.isdir(cocoapods_folder):
        input_folders.append(cocoapods_folder)

    # Still no input folder?
    if not input_folders and not carthage_folder and not cocoapods_folder:
        print 'Input folder(s) could not be detected, please specify it with -i or --input'
        sys.exit(2)
    elif not input_folders and (carthage_folder or cocoapods_folder):
        folders_as_files = []
        if carthage_folder:
            folders_as_files.append(carthage_folder)
        if cocoapods_folder:
            folders_as_files.append(cocoapods_folder)

        print "Input folder(s) {} doesn't exist or is not a folder".format(' and '.join(folders_as_files))
        sys.exit(2)
    elif not quiet:
        print 'Input folder(s): {}'.format(' and '.join(input_folders))

    return input_folders


def find_output_folder(quiet):
    """Finds the output folder based on the location of the Settings.bundle."""

    # Find the Settings.bundle
    output_folder = find_folder(os.getcwd(), 'Settings.bundle')

    # Still no output folder?
    if output_folder is None:
        print 'Output folder could not be detected, please specify it with -o or --output'
        sys.exit(2)
    elif not os.path.isdir(output_folder):
        print 'Output folder ' + output_folder + "doesn't exist or is not a folder"
        sys.exit(2)
    elif not quiet:
        print 'Output folder: ' + str(output_folder)

    return output_folder


def find_folder(base_path, search):
    """Finds a folder recursively."""

    # First look in the script's folder
    if search.startswith(os.path.basename(base_path)) and os.path.isdir(base_path):
        return base_path
    if os.path.isdir(os.path.join(base_path, search)):
        return os.path.join(base_path, search)

    # Look in subfolders
    for root, dirs, _ in os.walk(base_path):
        for dir_name in dirs:
            if search.startswith(dir_name):
                result = os.path.join(root, search)
                if os.path.isdir(result):
                    return result

    parent_path = os.path.abspath(os.path.join(base_path, '..'))

    # Try parent folder if it contains a Cartfile
    if os.path.exists(os.path.join(parent_path, 'Cartfile')):
        return find_folder(parent_path, search)

    # Try parent folder if it contains a Podfile
    if os.path.exists(os.path.join(parent_path, 'Podfile')):
        return find_folder(parent_path, search)

    return None


def generate(input_folders, output_folder, max_depth, clean_up, quiet):
    """Generates the acknowledgements."""
    frameworks = []

    # Create license folder path
    plists_path = os.path.join(output_folder, 'Licenses')
    if not os.path.exists(plists_path):
        if not quiet:
            print 'Creating Licenses folder'
        os.makedirs(plists_path)
    elif clean_up:
        if not quiet:
            print 'Removing old license plists'
        remove_files(plists_path, ".plist", quiet)

    # Scan the input folder for licenses
    if not quiet:
        print 'Searching licenses...'

    for input_folder in input_folders:
        for root, _, files in os.walk(input_folder):
            for file_name in files:
                # Ignore licenses in deep folders
                relative_path = os.path.relpath(root, input_folder)
                if relative_path.count(os.path.sep) >= max_depth:
                    continue

                # Look for license files
                if file_name.endswith('LICENSE') or file_name.endswith('LICENSE.txt'):
                    license_path = os.path.join(root, file_name)

                    # We found a license
                    framework = os.path.basename(os.path.dirname(license_path))
                    frameworks.append(framework)
                    if not quiet:
                        print 'Creating license plist for ' + framework

                    # Generate a plist
                    plist_path = os.path.join(plists_path, framework + '.plist')
                    create_license_plist(license_path, plist_path)

    # Did we find any licenses?
    if not quiet and not frameworks:
        print 'No licenses found'

    # Create the acknowledgements plist
    if not quiet:
        print 'Creating acknowledgements plist'

    plist_path = os.path.join(output_folder, 'Acknowledgements.plist')
    create_acknowledgements_plist(frameworks, plist_path)


def create_license_plist(license_path, plist_path):
    """Generates a plist for a single license, start with reading the license."""

    # Read and clean up the text
    license_text = codecs.open(license_path, 'r', 'utf-8').read()
    license_text = license_text.replace('  ', ' ')
    license_text = re.sub(
        r'(\S)[ \t]*(?:\r\n|\n)[ \t]*(\S)', '\\1 \\2',
        license_text
    )

    # Create the plist
    plistlib.writePlist({
        'PreferenceSpecifiers': [{
            'Type': 'PSGroupSpecifier',
            'FooterText': license_text
        }]
    }, plist_path)


def create_acknowledgements_plist(frameworks, plist_path):
    """Generates a plist combining all the licenses."""
    licenses = []

    # Walk through the frameworks
    for framework in frameworks:
        licenses.append({
            'Type': 'PSChildPaneSpecifier',
            'File': 'Licenses/' + framework, 'Title': framework
        })

    # Create the plist
    plistlib.writePlist(
        {'PreferenceSpecifiers': licenses},
        plist_path
    )


def remove_files(folder, extension, quiet):
    """Removes files with a specific extension from a folder."""

    for root, _, files in os.walk(folder):
        for file_name in files:
            if file_name.endswith(extension):
                full_path = os.path.join(root, file_name)
                try:
                    os.remove(full_path)
                except OSError:
                    if not quiet:
                        print 'Could not remove ' + full_path


# Main entry point
if __name__ == "__main__":
    main()
