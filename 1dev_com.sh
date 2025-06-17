#!/bin/bash

# Check if development branch exists
if ! git show-ref --verify --quiet refs/heads/development; then
    echo "Development branch does not exist. Creating it..."
    git checkout -b development
fi

# Switch to development branch
git checkout development

# Ask for commit label
read -p "Enter a label for your commit: " commit_label

# Add all changes
git add .

# Commit with the label
git commit -m "$commit_label"

# Push to development branch
git push gitrepo development

echo "Changes have been committed and pushed to development branch." 