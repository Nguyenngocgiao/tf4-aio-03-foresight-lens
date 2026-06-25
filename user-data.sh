#!/bin/bash
yum update -y
yum install -y python3 python3-pip tar
cd /home/ec2-user
curl -o engine-skeleton.tar.gz "https://tf4-cdo-mock-test-1782359769.s3.us-east-1.amazonaws.com/engine-skeleton.tar.gz?X-Amz-Algorithm=AWS4-HMAC-SHA256URL_PLACEHOLDERX-Amz-Credential=AKIA3B5MDX6KYKFTOYWA%2F20260625%2Fus-east-1%2Fs3%2Faws4_requestURL_PLACEHOLDERX-Amz-Date=20260625T035622ZURL_PLACEHOLDERX-Amz-Expires=3600URL_PLACEHOLDERX-Amz-SignedHeaders=hostURL_PLACEHOLDERX-Amz-Signature=12ac008be3251c0aeb9be192e0837c72543ebbcd522bae0850ae1d221490e27e"
tar -xzvf engine-skeleton.tar.gz
cd engine-skeleton
pip3 install -r requirements.txt
# Run uvicorn on port 80 as root
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 80 > /home/ec2-user/uvicorn.log 2>&1 &
