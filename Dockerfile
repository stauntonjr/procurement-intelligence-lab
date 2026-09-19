FROM python:3.13-slim AS build

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.13-slim

RUN groupadd --gid 10001 inspector \
    && useradd --uid 10001 --gid inspector --create-home --shell /usr/sbin/nologin inspector
COPY --from=build /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels

USER inspector
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000

CMD ["python", "-m", "procurement_intelligence_lab.interfaces.web", "--host", "0.0.0.0", "--port", "8000"]
