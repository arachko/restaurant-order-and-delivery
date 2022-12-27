#!/bin/bash
pip install --upgrade awscli
aws --version
pip install virtualenv
virtualenv /tmp/venv
. /tmp/venv/bin/activate
export PIP_WHEEL=.
pip install --upgrade chalice
pip install -r requirements.txt
export PYTHONPATH=.
which chalice
chalice --version
echo $APP_S3_BUCKET
chalice package --merge-template pipeline.json tmp/packaged/
aws cloudformation package --template-file /tmp/packaged/sam.json --s3-bucket "${APP_S3_BUCKET}" --output-template-file transformed.yaml
