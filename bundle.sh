#!/bin/sh
# Call this to bundle the repository as a .zip, suitable for use with the
# package manager. This simply throws the entire current state of the repo
# into a folder after copying the repo and then cleaning it. Do this after
# committing to bundle the agent with new changes.
#
# Note that the server automatically renames the bundle and package after
# being installed, based on the contents of agent.json.

# Nuke the build, if one already exists
echo "Deleting build output, if it exists"
rm -rf ./build

# Create the build output
echo "Copying files to build output"
mkdir ./build

# Copy the source directory, resources, and the git repo
cp ./src ./build/src -r
cp ./resources ./build/resources -r
cp ./contribs ./build/contribs -r
cp ./.git ./build/.git -r 

# Copy all files shallowly, ignore errors
cp ./* ./build/ 2>/dev/null

# Move to the build folder, then use git to remove all untracked files and
# changes.
echo "Removing uncommitted files from build output"
cd ./build
git clean -f -x -d

# Remove the git folder itself.
echo "Removing .git"
rm -rf ./.git

echo "Invoking metadata generator"
python3 -m src.meta.generate_metadata

echo "Invoking Makefile editor"
python3 -m src.meta.replace_install

# echo "Invoking compose editor"
# python3 -m src.meta.generate_compose

# Zip the remaining contents of the directory. Make a copy in the parent folder, too.
echo "Zipping to pygin-build.zip"
zip -r pygin-build.zip .
cp ./pygin-build.zip ../pygin-build.zip

echo "Done. A Docker image of unrdeaddrop/pygin:$( python3 -m src.meta.agent ) has been assumed."
echo "Please ensure that this image has been published before attempting to install the package."
echo "You can publish an image by pushing your changes to GitHub."







