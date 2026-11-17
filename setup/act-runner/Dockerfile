FROM node:24.22.2-trixie-slim@sha256:54f84b4cf8432b21aaffd5d3ce8d41e12cea0d10d33c09d2f3c9879d49d6b446

ARG UV_VERSION=0.10.8
ARG UV_SHA256_X86_64=f0c566b55683395a62fefb9261a060fa09824914b5682c3b9629fa154762ae2f
ARG UV_SHA256_AARCH64=661860e954f87dcd823251191866af3486484d1a9df60eed56f4586ed7559e3d
ARG PYTHON_VERSION=3.12.13

ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    UV_CACHE_DIR=/opt/uv/cache \
    UV_LINK_MODE=copy

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates git \
 && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    case "$(uname -m)" in \
      x86_64) target=x86_64-unknown-linux-gnu; sum="$UV_SHA256_X86_64" ;; \
      aarch64) target=aarch64-unknown-linux-gnu; sum="$UV_SHA256_AARCH64" ;; \
      *) echo "Không có bản uv cho kiến trúc $(uname -m)" >&2; exit 1 ;; \
    esac; \
    node -e 'const [u, o] = process.argv.slice(1); fetch(u).then(r => { if (!r.ok) throw new Error("HTTP " + r.status + " " + u); return r.arrayBuffer(); }).then(b => require("fs").writeFileSync(o, Buffer.from(b))).catch(e => { console.error("Tải lỗi: " + ((e.cause && e.cause.code) || e.message)); process.exit(1); })' \
      "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${target}.tar.gz" /tmp/uv.tar.gz; \
    echo "${sum}  /tmp/uv.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/uv.tar.gz -C /usr/local/bin --strip-components=1 "uv-${target}/uv"; \
    rm /tmp/uv.tar.gz; \
    uv --version

RUN uv python install "${PYTHON_VERSION}"

COPY requirements-ci.txt /opt/uv/requirements-ci.txt
RUN uv venv --python "${PYTHON_VERSION}" /tmp/seed \
 && uv pip install --python /tmp/seed/bin/python -r /opt/uv/requirements-ci.txt \
 && rm -rf /tmp/seed

ENV UV_PYTHON_DOWNLOADS=never \
    UV_OFFLINE=1

LABEL devops-track.act-runner="1.0" \
      org.opencontainers.image.title="devops-track act runner" \
      org.opencontainers.image.description="node:24.22.2-trixie-slim + git, ca-certificates, uv 0.10.8, CPython 3.12.13, cache wheel của Olist Shop"
