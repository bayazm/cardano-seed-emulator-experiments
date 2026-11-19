FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-cryptography \
        ca-certificates \
        iproute2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENTRYPOINT ["python3"]
