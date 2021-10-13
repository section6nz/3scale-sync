FROM registry.access.redhat.com/ubi8/python-39:1-18

ARG CREATED_AT
ARG GITHUB_SHA

LABEL org.opencontainers.image.created="$CREATED_AT"
LABEL org.opencontainers.image.revision="$GITHUB_SHA"

COPY . /opt/3scale-sync/

WORKDIR /opt/3scale-sync

USER root
RUN chmod +x main.py
USER 1001

RUN pip install -r requirements.txt

CMD ["/opt/3scale-sync/main.py", "--help"]
