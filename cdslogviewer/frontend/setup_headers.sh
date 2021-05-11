#!/bin/sh

echo Setting up deploy credentials for pluto-headers...

if [ "${HEADERS_DEPLOY_USER}" == "" ] || [ "${HEADERS_DEPLOY_TOKEN}" == "" ]; then
    echo You must configure HEADERS_DEPLOY_USER and HEADERS_DEPLOY_TOKEN in the CI settings before this will build
    exit 1
fi

cat << EOF > ~/.gitconfig
[credential]
	helper = store
EOF

echo https://${HEADERS_DEPLOY_USER}:${HEADERS_DEPLOY_TOKEN}@gitlab.com > ~/.git-credentials

