chalice generate-pipeline pipeline.json
chalice package --merge-template pipeline.json tmp/packaged/
aws cloudformation package --template-file tmp/packaged/sam.json --s3-bucket restaurant-order-and-delivery-app-dev --output-template-file tmp/packaged.yaml
aws cloudformation deploy --template-file ./packaged.yaml --stack-name restaurant-menu-and-delivery-dev --capabilities CAPABILITY_IAM