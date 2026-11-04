FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ASSINA_MODE=homologacao \
    ASSINA_HOST=0.0.0.0 \
    ASSINA_DATA=/data

WORKDIR /app
COPY requirements.lock ./requirements.lock
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.lock \
    && python -m pip check

# Copy only runtime inputs. Neither local data nor keys enter the image.
COPY backend ./backend
COPY web ./web
COPY examples/exemplo-ficticio.pdf ./examples/exemplo-ficticio.pdf
COPY tools/healthcheck.py ./tools/healthcheck.py
COPY run.py ./run.py
RUN mkdir -p /data \
    && chown 10001:10001 /data \
    && chmod 700 /data \
    && python -m compileall -q backend run.py

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "tools/healthcheck.py"]
CMD ["python", "run.py"]
