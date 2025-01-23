FROM node:20.13.0-slim as node
FROM python:3.12-slim as devcontainer

# install UV
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

# Install required packages for Flutter development
RUN apt-get update -y && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    apt-transport-https \
    zip unzip \
    sudo \
    graphviz graphviz-dev git \
    wget \
    xz-utils \
    libglu1-mesa \
    chromium \
    clang \
    cmake \
    ninja-build \
    pkg-config \
    libgtk-3-dev \
    liblzma-dev

# Install Docker cli
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
RUN echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null


# Install Google cloud cli
RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

# Install terraform
RUN wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list

   RUN apt-get update -y && apt-get install -y \
    docker-ce docker-ce-cli containerd.io docker-compose-plugin \
    google-cloud-cli google-cloud-cli-app-engine-python google-cloud-cli-app-engine-python-extras google-cloud-cli-tests kubectl google-cloud-cli-minikube google-cloud-cli-cloud-run-proxy google-cloud-cli-cloud-build-local \
    terraform

COPY --from=node /usr/local/include/ /usr/local/include/
COPY --from=node /usr/local/lib/ /usr/local/lib/
COPY --from=node /usr/local/bin/ /usr/local/bin/

# Install aws cli
# See https://docs.aws.amazon.com/ja_jp/cli/latest/userguide/getting-started-install.html
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install --update

RUN terraform -install-autocomplete

# Install JDK and set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
RUN apt-get update && apt-get install -y openjdk-17-jdk

# Install Android SDK
ENV ANDROID_SDK_ROOT=/usr/local/android-sdk
ENV ANDROID_HOME=${ANDROID_SDK_ROOT}
ENV PATH=${PATH}:${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools

RUN mkdir -p ${ANDROID_SDK_ROOT} && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O android-sdk.zip && \
    unzip -q android-sdk.zip -d ${ANDROID_SDK_ROOT}/cmdline-tools && \
    mv ${ANDROID_SDK_ROOT}/cmdline-tools/cmdline-tools ${ANDROID_SDK_ROOT}/cmdline-tools/latest && \
    rm android-sdk.zip

# Install Android SDK components
ENV PATH=${PATH}:${JAVA_HOME}/bin
RUN yes | sdkmanager --licenses && \
    sdkmanager "platform-tools" "platforms;android-33" "build-tools;33.0.0"

# Install Flutter SDK
ENV FLUTTER_HOME=/usr/local/flutter
ENV FLUTTER_VERSION=3.19.0
RUN git clone https://github.com/flutter/flutter.git ${FLUTTER_HOME} && \
    cd ${FLUTTER_HOME} && \
    git checkout ${FLUTTER_VERSION}

# Add flutter to PATH
ENV PATH="${FLUTTER_HOME}/bin:${PATH}"

# Install Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# Configure Flutter
RUN flutter channel stable && \
    flutter upgrade && \
    flutter config --no-analytics && \
    flutter config --enable-web && \
    flutter doctor

# Set display for Flutter web development
ENV DISPLAY=:0
ENV CHROME_EXECUTABLE=/usr/bin/google-chrome

# Set the default shell to bash
SHELL ["/bin/bash", "-c"]
