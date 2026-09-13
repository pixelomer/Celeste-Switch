# syntax=docker/dockerfile:1

# Only host tools enter the image. Mount a source checkout and caller-owned
# inputs at runtime; generated installations must never become image layers.
FROM python@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS python
COPY scripts/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt \
      pefile==2024.8.26 setuptools==80.9.0

FROM mcr.microsoft.com/dotnet/sdk@sha256:20387c6674c30e46def0cc8cb557bd2a69b35afdf18c19c3694638d0a90897e4 AS dotnet9
FROM mcr.microsoft.com/dotnet/sdk@sha256:4ea6fe75dd36706bb6d8c3c293d4c4315840f5d76ea28ac97def77e3ec487fa5 AS dotnet10
FROM devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282

# Administrative privileges are used only to assemble the host toolchain.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bison bubblewrap build-essential ca-certificates clang cmake curl flex git \
      libcurl4-openssl-dev libicu-dev libkrb5-dev liblttng-ust-dev libnuma-dev \
      libssl-dev libunwind-dev lld llvm meson mono-devel ninja-build openjdk-17-jdk-headless \
      patch pkg-config python3-mako util-linux zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

COPY --from=python /usr/local/ /usr/local/
COPY --from=dotnet9 /usr/share/dotnet/ /usr/share/dotnet/
COPY --from=dotnet10 /usr/share/dotnet/ /usr/share/dotnet/
# The network-isolated installer intentionally exposes only /usr.
RUN ln -s /usr/share/dotnet/dotnet /usr/bin/dotnet

ARG BUILDER_UID=1000
ARG BUILDER_GID=1000
RUN groupadd --gid "${BUILDER_GID}" builder \
 && useradd --uid "${BUILDER_UID}" --gid builder --create-home builder \
 && mkdir /work \
 && chown builder:builder /work

ENV DEVKITPRO=/opt/devkitpro \
    DEVKITA64=/opt/devkitpro/devkitA64 \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    DOTNET_CLI_HOME=/home/builder \
    PATH=/opt/devkitpro/devkitA64/bin:/opt/devkitpro/tools/bin:/opt/devkitpro/portlibs/switch/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

USER builder
WORKDIR /work
ENTRYPOINT ["python3", "build.py"]
