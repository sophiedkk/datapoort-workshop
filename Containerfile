# Container for building the workshop handouts: ImageMagick, rsvg-convert, the Lexend font
# and the Python dependencies. Usage: see README.md.
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends imagemagick librsvg2-bin fontconfig curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Debian's ImageMagick policy blocks PDF output; the per-archetype sheet.pdf files need it.
RUN sed -i 's/<policy domain="coder" rights="none" pattern="PDF" \/>//' /etc/ImageMagick-7/policy.xml || true

# Lexend (SIL Open Font License): the variable font plus static SemiBold and ExtraBold.
RUN mkdir -p /usr/share/fonts/truetype/lexend && cd /usr/share/fonts/truetype/lexend \
 && curl -fsSL -o Lexend-VariableFont_wght.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/lexend/Lexend%5Bwght%5D.ttf" \
 && curl -fsSL -o OFL.txt "https://raw.githubusercontent.com/google/fonts/main/ofl/lexend/OFL.txt" \
 && for w in SemiBold ExtraBold; do \
      curl -fsSL -o "Lexend-$w.ttf" "https://raw.githubusercontent.com/googlefonts/lexend/main/fonts/lexend/ttf/Lexend-$w.ttf"; \
    done \
 && fc-cache -f

# Python dependencies live outside /work, so the mounted project's own .venv is left alone.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_CACHE_DIR=/tmp/uv-cache UV_NO_SYNC=1
COPY pyproject.toml uv.lock /tmp/project/
RUN cd /tmp/project && uv sync --frozen && chmod -R a+rX /opt/venv && rm -rf /tmp/uv-cache

WORKDIR /work
CMD ["handouts/build.sh"]
