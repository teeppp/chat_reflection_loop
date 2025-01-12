FROM node:20.13.0-slim as node
FROM python:3.12-slim as devcontainer

# install UV
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

RUN apt-get update -y && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    apt-transport-https \
    zip unzip \
    sudo \
    graphviz graphviz-dev git

# Install Docker cli
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
RUN echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null


# Install Google cloud cli
RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

RUN apt-get update -y && apt-get install -y \
    docker-ce docker-ce-cli containerd.io docker-compose-plugin \
    google-cloud-cli google-cloud-cli-app-engine-python google-cloud-cli-app-engine-python-extras google-cloud-cli-tests kubectl google-cloud-cli-minikube google-cloud-cli-cloud-run-proxy google-cloud-cli-cloud-build-local

COPY --from=node /usr/local/include/ /usr/local/include/
COPY --from=node /usr/local/lib/ /usr/local/lib/
COPY --from=node /usr/local/bin/ /usr/local/bin/