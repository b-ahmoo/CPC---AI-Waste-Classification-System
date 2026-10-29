"""Waste Identification & Classification (WIC) — domain classes.

This module has no Flask imports, so it can be used and tested
on its own, without the web interface.
"""

import base64
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

DEFAULT_PROMPT = (
    "You are a waste-sorting assistant for Germany. Identify every separate "
    "waste item visible in the image. For each item report:\n"
    "- item_name: a short English name\n"
    "- material: exactly one of Kunststoff, Metall, Verbundstoff, Papier, Pappe, "
    "Glas, Bio, Batterie, Elektro, Schadstoff, Rest\n"
    "- container: one of can, plastic_bottle, glass_bottle, other\n"
    "- beverage: true if it is (or held) a drink, otherwise false\n"
    "- pfand_logo_visible: true only if a German deposit (Pfand / DPG Einweg) "
    "logo or a Mehrweg label is visible on the item, otherwise false\n"
    "Reply only with JSON in this shape: "
    '{"items": [{"item_name": "...", "material": "...", "container": "...", '
    '"beverage": false, "pfand_logo_visible": false}]}. '
    'If you cannot identify an item, use "nicht erkannt" as item_name and '
    "material. If there is no waste item at all, return an empty list."
)


class ClassificationError(Exception):
    """Raised when an image cannot be classified (bad file, API failure)."""


@dataclass
class ClassificationResult:
    item_name: str
    material: str
    bin_type: str
    is_pfand: bool
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict:
        return asdict(self)


class BinMapper:
    """Maps a material to a German bin using the rules in rules.json."""

    def __init__(self, rules_path: str = "rules.json"):
        self.rules_path = rules_path
        self.rules = self.load_rules()

    def load_rules(self) -> dict:
        path = Path(self.rules_path)
        if not path.is_absolute():
            path = Path(__file__).parent / path
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def map_to_bin(self, material: str) -> str:
        return self.rules["material_to_bin"].get(material, self.rules["unknown_label"])

    def is_pfand(self, item) -> bool:
        """Decide Pfand from what the AI saw, using the rules in rules.json.

        `item` is the AI's dict for one item (a plain name string also works).
        Pfand if any rule matches: the Pfand logo is visible, the item is a
        drink in a container type that always carries Pfand in Germany, or
        its name contains a Pfand keyword.
        """
        if isinstance(item, str):
            item = {"item_name": item}
        pfand_rules = self.rules["pfand"]

        if pfand_rules["logo_visible_means_pfand"] and item.get("pfand_logo_visible") is True:
            return True
        if item.get("beverage") is True and item.get("container") in pfand_rules["beverage_containers"]:
            return True
        name = str(item.get("item_name", "")).lower()
        return any(keyword in name for keyword in pfand_rules["keywords"])


class WasteClassifier:
    """Sends an image to a vision model (Azure OpenAI or any OpenAI-compatible API)
    and turns the answer into results.

    The API client can be passed in from outside (dependency injection), so
    tests and the demo mode can use a fake client instead of calling OpenAI.
    """

    def __init__(self, api_key=None, client=None, bin_mapper=None,
                 prompt_template=DEFAULT_PROMPT, timeout=10, model="gpt-4o-mini",
                 base_url=None):
        self.api_key = api_key
        self.prompt_template = prompt_template
        self.timeout = timeout
        self.model = model
        self.bin_mapper = bin_mapper or BinMapper()
        if client is None:
            from openai import OpenAI  # imported here so tests don't need a key
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.client = client

    def classify_image(self, image_bytes: bytes) -> list:
        mime_type = self._validate(image_bytes)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")  # stays in memory
        raw = self._call_api(image_b64, mime_type)
        return self._parse_response(raw)

    def _validate(self, image_bytes: bytes) -> str:
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise ClassificationError("Image is larger than 10 MB.")
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if image_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        raise ClassificationError("Only JPEG and PNG images are supported.")

    def _call_api(self, image_b64: str, mime_type: str) -> dict:
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": self.prompt_template},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
            ],
        }]
        try:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    messages=messages,
                )
            except Exception as e:
                # Some OpenAI-compatible providers reject JSON mode: retry without it.
                if type(e).__name__ != "BadRequestError":
                    raise
                response = self.client.chat.completions.create(model=self.model, messages=messages)
            return json.loads(self._strip_code_fence(response.choices[0].message.content))
        except json.JSONDecodeError as e:
            raise ClassificationError("The AI returned an unreadable answer.") from e
        except Exception as e:  # timeouts, network errors, invalid key, no credit
            raise ClassificationError(f"Classification failed: {e}") from e

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        """Remove ```json ... ``` wrapping that some models add around JSON."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else ""
            text = text.rsplit("```", 1)[0]
        return text.strip()

    def _parse_response(self, raw: dict) -> list:
        unknown = self.bin_mapper.rules["unknown_label"]
        results = []
        for item in raw.get("items", []):
            name = str(item.get("item_name") or unknown)
            material = str(item.get("material") or unknown)
            pfand = self.bin_mapper.is_pfand(item)
            if pfand:
                bin_type = self.bin_mapper.rules["pfand"]["bin"]
            else:
                bin_type = self.bin_mapper.map_to_bin(material)
            results.append(ClassificationResult(name, material, bin_type, pfand))
        if not results:
            results.append(ClassificationResult(unknown, unknown, unknown, False))
        return results


class FakeClient:
    """Stands in for the OpenAI client: no network, no key, fixed answer.

    Used for the demo mode (no API key available) and for unit tests.
    """

    def __init__(self, items=None):
        self.items = items if items is not None else [
            {"item_name": "PET Bottle", "material": "Kunststoff", "container": "plastic_bottle",
             "beverage": True, "pfand_logo_visible": True},
            {"item_name": "Newspaper", "material": "Papier", "container": "other",
             "beverage": False, "pfand_logo_visible": False},
        ]
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        content = json.dumps({"items": self.items})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
