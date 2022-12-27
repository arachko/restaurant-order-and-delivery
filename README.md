API Documentation (Postman):
https://documenter.getpostman.com/view/7172530/2s8YzL5n1t#3564b29a-ae68-4d4a-8da4-8f7561c71d60



chalice generate-pipeline pipeline.json
chalice package --merge-template pipeline.json tmp/packaged/
aws cloudformation package --template-file tmp/packaged/sam.json --s3-bucket restmonster-backend-app-dev --output-template-file tmp/packaged.yaml
aws cloudformation deploy --template-file ./packaged.yaml --stack-name restaurant-menu-and-delivery-dev --capabilities CAPABILITY_IAM