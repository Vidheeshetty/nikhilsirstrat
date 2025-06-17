#!/bin/bash

# Ask for the same label used in development
read -p "Enter the same label used in development: " commit_label

# Switch to main branch
git checkout main

# Merge development into main
git merge development

# Push to main branch
git push gitrepo main

# Switch back to development
git checkout development

echo "Main branch has been synchronized with development branch." 