#!/bin/bash
docker pull amazon/dynamodb-local
docker stop localdb;
docker run --rm --name localdb -d -p 9000:8000 amazon/dynamodb-local;
aws dynamodb create-table \
--table-name local \
--attribute-definitions \
AttributeName=partkey,\
AttributeType=S AttributeName=sortkey,\
AttributeType=S AttributeName=gsi_user_orders_partkey,\
AttributeType=S AttributeName=gsi_user_orders_sortkey,\
AttributeType=S \
--key-schema AttributeName=partkey,KeyType=HASH AttributeName=sortkey,KeyType=RANGE \
--provisioned-throughput ReadCapacityUnits=1000,WriteCapacityUnits=1000 \
--endpoint-url http://localhost:9000 \
--global-secondary-indexes '[{"IndexName":"gsi_user_orders", "KeySchema":[{"AttributeName":"gsi_user_orders_partkey","KeyType":"HASH"},{"AttributeName":"gsi_user_orders_sortkey","KeyType":"RANGE"}], "ProvisionedThroughput":{"ReadCapacityUnits":10, "WriteCapacityUnits":5},"Projection":{"ProjectionType":"ALL"}}]'
#IndexName=gsi_user_orders,\
#KeySchema=["{AttributeName=gsi_user_orders_partkey,KeyType=HASH}","{AttributeName=gsi_user_orders_sortkey,KeyType=RANGE}"],\
#Projection="{ProjectionType=ALL}",\
#ProvisionedThroughput="{ReadCapacityUnits=10,WriteCapacityUnits=10}"



#--global-secondary-indexes '[{"Create":{"IndexName":"gsi_user_orders", "KeySchema":[{"AttributeName":"id_","KeyType":"HASH"}], "ProvisionedThroughput":{"ReadCapacityUnits":10, "WriteCapacityUnits":5},"Projection":{"ProjectionType":"ALL"}}}]'
#aws dynamodb update-table --endpoint-url http://localhost:9000 --table-name local --attribute-definitions AttributeName=id_,AttributeType=S --global-secondary-index-updates '[{"Create":{"IndexName":"id_-index", "KeySchema":[{"AttributeName":"id_","KeyType":"HASH"}], "ProvisionedThroughput":{"ReadCapacityUnits":10, "WriteCapacityUnits":5},"Projection":{"ProjectionType":"ALL"}}}]'
