#!/bin/bash
# Run this script with your GitHub Personal Access Token
# Usage: ./push_to_github.sh YOUR_GITHUB_TOKEN

TOKEN=$1

if [ -z "$TOKEN" ]; then
    echo "Usage: ./push_to_github.sh YOUR_GITHUB_TOKEN"
    echo ""
    echo "Get a token from: https://github.com/settings/tokens"
    echo "Required scopes: repo"
    exit 1
fi

git push https://$TOKEN@github.com/AtharvRoy/CENEX-AI-v1.5.git main
