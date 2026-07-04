# docker/

Auxiliary Dockerfiles that aren't the main build. The primary `Dockerfile` and
`docker-compose.yml` stay at the repo root (Docker/Compose look there by default, and
every CI workflow assumes that path).

- **`rabbitmq.Dockerfile`** - RabbitMQ broker image for docker-compose's local async queue path. Built via `docker-compose.yml`'s `rabbitmq` service (`dockerfile: docker/rabbitmq.Dockerfile`).
- **`lambda-rie.Dockerfile`** - Local-only wrapper adding the AWS Lambda Runtime Interface Emulator on top of `lambda/Dockerfile`, so the worker image can be invoked locally like real Lambda. Not used by CI or `deploy.yml`. See the file's own header comment for build/run/invoke commands.
