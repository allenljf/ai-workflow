# Build from examples/fde/python; digest pinned after local pull 2026-10-08.
FROM python:3.12.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c
WORKDIR /app
COPY pyproject.toml ./
COPY fde_lab ./fde_lab
RUN pip install --no-cache-dir '.[postgres]' && useradd --uid 10001 --create-home fde && mkdir /state && chown fde:fde /state
USER 10001
ENV FDE_BIND=0.0.0.0 FDE_STATE_DIR=/state PORT=8080
EXPOSE 8080
ENTRYPOINT ["python", "-m", "fde_lab.api"]
