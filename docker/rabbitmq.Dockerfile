FROM alpine:3.24
RUN apk add --no-cache rabbitmq-server
ENV RABBITMQ_DEFAULT_USER=shelter
ENV RABBITMQ_DEFAULT_PASS=pulse
EXPOSE 5672
# alpine's rabbitmq-server package already creates this user and owns
# /var/lib/rabbitmq + /var/log/rabbitmq - no manual useradd/chown needed.
USER rabbitmq
CMD ["rabbitmq-server"]
