#!/bin/bash

# Ask for version number
read -p "Enter version number (e.g., 1.0.0): " version_number
read -p "Enter release description: " release_description

# Create version tag
version_tag="v$version_number"

# Switch to development branch
git checkout development

# Add all changes
git add .

# Commit with version information
git commit -m "Release $version_tag: $release_description"

# Create tag
git tag -a "$version_tag" -m "Version $version_number: $release_description"

# Push development branch and tags
git push gitrepo development
git push gitrepo --tags

# Switch to main branch
git checkout main

# Merge development into main
git merge development

# Push main branch
git push gitrepo main

# Switch back to development
git checkout development

echo "Version $version_number has been released and synchronized across both branches." 