chalice generate-pipeline pipeline.json
chalice package --merge-template pipeline.json out/
aws cloudformation package --template-file out/sam.json --s3-bucket restaurant-menu-and-order-app-dev --output-template-file packaged.yaml
aws cloudformation deploy --template-file /Users/rachko.a/PycharmProjects/restaurant-menu-and-delivery/packaged.yaml --stack-name restaurant-menu-and-delivery-dev --capabilities CAPABILITY_IAM