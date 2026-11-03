"""Shared test setup: write generated PDFs to a temp folder, not /app."""

import os
import tempfile

os.environ.setdefault("PDF_DIR", tempfile.mkdtemp(prefix="solar_pdfs_"))
