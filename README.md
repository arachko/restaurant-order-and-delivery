API Documentation (Postman):
https://documenter.getpostman.com/view/7172530/2s8YzL5n1t#3564b29a-ae68-4d4a-8da4-8f7561c71d60



***
### **Initial Deployment AWS:**  
`chalice generate-pipeline pipeline.json`  
_In created pipeline.json fix python image to "standard:5.0": "CodeBuildImage": {"Default": "aws/codebuild/standard:5.0"...}_  
`./build-dev.sh`  
`aws cloudformation deploy --template-file ./transformed.yaml --s3-bucket restmonster-backend-app-dev --stack-name restmonster-backendBetaStack --capabilities CAPABILITY_IAM`
