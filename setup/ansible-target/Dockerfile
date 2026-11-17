FROM python:3.12.16-slim-trixie

RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-server sudo systemd \
 && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_*

COPY requirements-worker.txt /srv/wheels/requirements.txt
RUN pip install --no-cache-dir --only-binary :all: packaging==26.3 \
 && pip download --no-cache-dir --only-binary :all: --dest /srv/wheels -r /srv/wheels/requirements.txt

COPY sshd_config /etc/ssh/sshd_config.d/devops-ex.conf
COPY entrypoint.sh /usr/local/sbin/devops-ex-target
RUN chmod 0755 /usr/local/sbin/devops-ex-target && mkdir -p /run/sshd && chmod 0755 /run/sshd

EXPOSE 22
ENTRYPOINT ["/usr/local/sbin/devops-ex-target"]
