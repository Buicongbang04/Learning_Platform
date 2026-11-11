FROM alpine:3.24.3@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a
RUN apk add --no-cache iproute2-tc=7.0.0-r0
LABEL org.opencontainers.image.title="devops-track/netem" \
      org.opencontainers.image.description="tc (iproute2) cho FaultInjector của testkit: thêm độ trễ netem vào network namespace của một container trong lab"
