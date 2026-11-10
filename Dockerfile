FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    ODP_DATA=/app/data/istat

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
RUN pip install . \
    && useradd --system --no-create-home --uid 10001 odp \
    && install -d -o odp /data

# The ISTAT files of the repository are inside the image (ODP_DATA); results are written to /data (a volume or a bind
# mount). Nothing needs the network or a privilege: run with --network none, --read-only, --cap-drop ALL and --tmpfs /tmp
# (matplotlib's cache).
USER odp
WORKDIR /data
VOLUME ["/data"]
ENTRYPOINT ["odp"]
CMD ["--help"]
