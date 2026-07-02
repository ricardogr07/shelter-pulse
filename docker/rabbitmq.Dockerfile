FROM alpine:latest
RUN apk add --no-cache rabbitmq-server
ENV RABBITMQ_DEFAULT_USER=shelter
ENV RABBITMQ_DEFAULT_PASS=pulse
EXPOSE 5672
CMD ["rabbitmq-server"]
