# Local-only wrapper around lambda/Dockerfile that adds the AWS Lambda Runtime
# Interface Emulator (RIE), so `docker run -p 9000:8080 ...` actually exposes
# the /2015-03-31/functions/function/invocations endpoint documented in
# lambda/Dockerfile's own header comment. awslambdaric alone (what
# lambda/Dockerfile installs) is only the Runtime Interface *Client* - it
# expects AWS_LAMBDA_RUNTIME_API to already be set by something, which is
# what RIE provides for local testing. AWS's own public.ecr.aws/lambda/*
# base images bundle RIE automatically; this project's lambda/Dockerfile
# builds from plain python:3.12-slim, so it doesn't get RIE for free.
#
# Not used by CI or deploy.yml - production still builds from
# lambda/Dockerfile directly. This exists purely for local debugging,
# equivalent to running Azurite/the Cosmos DB emulator for Azure.
#
# Build: docker build -f docker/lambda-rie.Dockerfile -t shelterpulse-worker-rie .
# Run:   docker run -p 9000:8080 -e API_URL=http://api:8000 -e INTERNAL_KEY=dev-key-123 \
#          --network shelter-pulse_default shelterpulse-worker-rie
# Invoke: curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
#           -d '{"Records": [{"body": "{\"job_id\": \"...\", \"type\": \"optimize_builder\", \"request\": {...}}"}]}'

FROM shelterpulse-worker-local

ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/local/bin/aws-lambda-rie
RUN chmod +x /usr/local/bin/aws-lambda-rie

ENTRYPOINT ["/usr/local/bin/aws-lambda-rie", ".venv/bin/python", "-m", "awslambdaric"]
CMD ["handler.handler"]
