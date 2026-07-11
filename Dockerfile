FROM python:3.11-alpine

# Install platform-specific build dependencies
ARG TARGETPLATFORM
ARG AEROFOIL_VERSION
ENV AEROFOIL_VERSION=$AEROFOIL_VERSION
RUN apk update && apk add --no-cache bash sudo \
    git \
    && if [ "$TARGETPLATFORM" = "linux/arm/v6" ] || [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        apk add --no-cache build-base gcc musl-dev jpeg-dev zlib-dev libffi-dev cairo-dev pango-dev gdk-pixbuf-dev; \
    fi

RUN mkdir /app

# Bundle a reproducible cheat database snapshot. Runtime queries use these
# local JSON files first and only contact the upstream source as a fallback.
ARG AEROFOIL_CHEATS_DB_REF=911426953758ea83569de183b8f65b6fa76ea901
RUN mkdir -p /opt/aerofoil-cheatdb \
    && cd /opt/aerofoil-cheatdb \
    && git init \
    && git remote add origin https://github.com/HamletDuFromage/switch-cheats-db.git \
    && git fetch --depth 1 origin "${AEROFOIL_CHEATS_DB_REF}" \
    && git checkout --detach FETCH_HEAD \
    && rm -rf .git
ENV AEROFOIL_CHEATS_DB_DIR=/opt/aerofoil-cheatdb
ENV AEROFOIL_CHEATS_REMOTE_FALLBACK=true

COPY ./app /app
COPY ./docker/run.sh /app/run.sh

COPY requirements.txt /tmp/

RUN pip install --no-cache-dir --requirement /tmp/requirements.txt && rm /tmp/requirements.txt

# Normalize CRLF to LF and ensure entrypoint is executable across platforms
RUN sed -i 's/\r$//' /app/run.sh && chmod +x /app/run.sh

RUN if [ "$TARGETPLATFORM" = "linux/arm/v6" ] || [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        apk del build-base gcc musl-dev jpeg-dev zlib-dev libffi-dev cairo-dev pango-dev gdk-pixbuf-dev; \
    fi

RUN mkdir -p /app/data

WORKDIR /app

ENTRYPOINT [ "/app/run.sh" ]
