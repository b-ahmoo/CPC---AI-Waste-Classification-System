"""Flask routes for the Waste Identification & Classification subsystem."""

import base64
import hashlib
import os
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, session

from app.subsystems.classification.classifier import (
    ClassificationError, FakeClient, WasteClassifier)
from app.models.scan import (find_by_hash, recent_scans, save_results,
                             user_has_scan)
from app.subsystems.classification.errors import ClassificationErrorHandler

classification_bp = Blueprint("classification", __name__)

_classifier = None
_demo_mode = False
_error_handler = ClassificationErrorHandler()


def _setting(*names, default=None):
    """First environment variable out of `names` that is set and not a template placeholder."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value and not value.startswith("your-"):
            return value
    return default


def get_classifier():
    """Real classifier if an API key is set, otherwise demo mode with sample results.

    Uses the team's Azure OpenAI settings (same as the chatbot). The OPENAI_* names
    are a fallback for running with plain OpenAI or another OpenAI-compatible API.
    """
    global _classifier, _demo_mode
    if _classifier is None:
        api_key = _setting("AZURE_OPENAI_API_KEY", "OPENAI_API_KEY", default="")
        base_url = _setting("AZURE_OPENAI_ENDPOINT", "OPENAI_BASE_URL")
        model = _setting("AZURE_OPENAI_DEPLOYMENT_NAME", "OPENAI_MODEL", default="gpt-4o-mini")
        if api_key:
            _classifier = WasteClassifier(api_key=api_key, base_url=base_url, model=model, timeout=40)
            _demo_mode = False
        else:
            _classifier = WasteClassifier(client=FakeClient(), model=model)
            _demo_mode = True
    return _classifier, _demo_mode


@classification_bp.route("/", methods=["GET", "POST"])
def classify():
    classifier, demo_mode = get_classifier()
    results, error, from_cache, image_url = None, None, False, None

    if request.method == "POST":
        file = request.files.get("image")
        if file is None or file.filename == "":
            error = "Please choose an image first."
        else:
            image_bytes = file.read()
            image_hash = hashlib.sha256(image_bytes).hexdigest()

            try:
                results = find_by_hash(image_hash)
                if results:
                    from_cache = True
                    # The answer is reused so the AI is not called twice, but this
                    # user still gets their own row, or the scan would be missing
                    # from their history just because someone else uploaded it first.
                    user_id = session.get("user_id")
                    if not demo_mode and user_id and not user_has_scan(image_hash, user_id):
                        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                        save_results([dict(r, timestamp=now) for r in results],
                                     image_hash, user_id=user_id)
                else:
                    results = [r.to_dict() for r in classifier.classify_image(image_bytes)]
                    if not demo_mode:  # don't store sample data
                        save_results(results, image_hash, user_id=session.get("user_id"))
            except Exception as e:  # bad image, API failure, database down, ...
                error, results = _error_handler.handle(e), None

            if results:
                mime = "image/png" if image_bytes.startswith(b"\x89PNG") else "image/jpeg"
                image_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"

    try:
        recent = recent_scans(user_id=session.get("user_id"))
    except Exception as e:  # the page still loads if the database is down
        _error_handler.handle(e)
        recent = []

    return render_template(
        "classification/index.html",
        results=results,
        error=error,
        from_cache=from_cache,
        image_url=image_url,
        demo_mode=demo_mode,
        recent=recent,
    )