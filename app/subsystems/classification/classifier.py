"""Waste Identification & Classification (WIC) — domain classes.

This module has no Flask imports, so it can be used and tested
on its own, without the web interface.
"""

import base64
import json
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


class ClassificationResult:
    """One identified waste item: what it is, what it is made of, and where it goes."""

    def __init__(self, item_name: str, material: str, bin_type: str,
                 is_pfand: bool = False, timestamp: str = None):
        # Every attribute is set through its setter, so the checks always run.
        self.item_name = item_name
        self.material = material
        self.bin_type = bin_type
        self.is_pfand = is_pfand
        self.timestamp = timestamp or self._current_timestamp()

    # --- Initialization methods ---------------------------------------------

    @staticmethod
    def _current_timestamp() -> str:
        """Current time in UTC as ISO 8601 text, e.g. 2026-10-29T10:15:00+00:00."""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @classmethod
    def from_dict(cls, data: dict) -> "ClassificationResult":
        """Build a result from a dictionary, e.g. a row read back from the database."""
        return cls(data["item_name"], data["material"], data["bin_type"],
                   data.get("is_pfand", False), data.get("timestamp"))

    # --- Getters and setters ------------------------------------------------

    @property
    def item_name(self) -> str:
        return self._item_name

    @item_name.setter
    def item_name(self, value: str):
        self._item_name = self._non_empty_text(value, "item_name")

    @property
    def material(self) -> str:
        return self._material

    @material.setter
    def material(self, value: str):
        self._material = self._non_empty_text(value, "material")

    @property
    def bin_type(self) -> str:
        return self._bin_type

    @bin_type.setter
    def bin_type(self, value: str):
        self._bin_type = self._non_empty_text(value, "bin_type")

    @property
    def is_pfand(self) -> bool:
        return self._is_pfand

    @is_pfand.setter
    def is_pfand(self, value: bool):
        self._is_pfand = bool(value)

    @property
    def timestamp(self) -> str:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: str):
        self._timestamp = self._non_empty_text(value, "timestamp")

    # --- Other methods ------------------------------------------------------

    @staticmethod
    def _non_empty_text(value, name: str) -> str:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValueError(f"{name} must not be empty.")
        return text

    def to_dict(self) -> dict:
        """Plain dictionary, used for saving to the database and showing on the page."""
        return {
            "item_name": self.item_name,
            "material": self.material,
            "bin_type": self.bin_type,
            "is_pfand": self.is_pfand,
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        return (f"ClassificationResult(item_name={self.item_name!r}, material={self.material!r}, "
                f"bin_type={self.bin_type!r}, is_pfand={self.is_pfand})")


class BinMapper:
    """Maps a material to a German bin using the rules in rules.json."""

    REQUIRED_KEYS = ("material_to_bin", "pfand", "unknown_label")

    def __init__(self, rules_path: str = "rules.json"):
        self._rules = {}
        self.rules_path = rules_path  # the setter loads the rules from this file

    # --- Initialization methods ---------------------------------------------

    def load_rules(self) -> dict:
        """Read rules.json, check it has every required section, and keep it."""
        path = Path(self._rules_path)
        if not path.is_absolute():
            path = Path(__file__).parent / path
        with open(path, encoding="utf-8") as f:
            rules = json.load(f)
        self.rules = rules  # goes through the setter, which validates
        return self._rules

    # --- Getters and setters ------------------------------------------------

    @property
    def rules_path(self) -> str:
        return self._rules_path

    @rules_path.setter
    def rules_path(self, value: str):
        """Changing the rules file loads the new rules straight away."""
        self._rules_path = ClassificationResult._non_empty_text(value, "rules_path")
        self.load_rules()

    @property
    def rules(self) -> dict:
        return self._rules

    @rules.setter
    def rules(self, value: dict):
        if not isinstance(value, dict):
            raise ValueError("rules must be a dictionary.")
        missing = [key for key in self.REQUIRED_KEYS if key not in value]
        if missing:
            raise ValueError(f"rules are missing: {', '.join(missing)}")
        self._rules = value

    @property
    def unknown_label(self) -> str:
        return self._rules["unknown_label"]

    @property
    def pfand_bin(self) -> str:
        return self._rules["pfand"]["bin"]

    # --- Other methods ------------------------------------------------------

    def map_to_bin(self, material: str) -> str:
        return self._rules["material_to_bin"].get(material, self.unknown_label)

    def is_pfand(self, item) -> bool:
        """Decide Pfand from what the AI saw, using the rules in rules.json.

        `item` is the AI's dict for one item (a plain name string also works).
        Pfand if any rule matches: the Pfand logo is visible, the item is a
        drink in a container type that always carries Pfand in Germany, or
        its name contains a Pfand keyword.
        """
        if isinstance(item, str):
            item = {"item_name": item}
        pfand_rules = self._rules["pfand"]

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
    tests and the demo mode can use a fake client instead of calling the API.
    """

    def __init__(self, api_key=None, client=None, bin_mapper=None,
                 prompt_template=DEFAULT_PROMPT, timeout=10, model="gpt-4o-mini",
                 base_url=None):
        self._api_key = api_key
        self._base_url = base_url
        self.timeout = timeout
        self.model = model
        self.prompt_template = prompt_template
        self.bin_mapper = bin_mapper or BinMapper()
        self._client_injected = client is not None
        self._client = client if client is not None else self._create_client()

    # --- Initialization methods ---------------------------------------------

    def _create_client(self):
        """Set up the connection to the API from the key, address and timeout."""
        from openai import OpenAI  # imported here so tests don't need the package configured
        return OpenAI(api_key=self._api_key, base_url=self._base_url, timeout=self._timeout)

    def _refresh_client(self):
        """Rebuild the API connection after a setting changed (not for injected clients)."""
        if not self._client_injected:
            self._client = self._create_client()

    # --- Getters and setters ------------------------------------------------

    @property
    def api_key(self):
        return self._api_key

    @api_key.setter
    def api_key(self, value):
        self._api_key = value
        self._refresh_client()

    @property
    def base_url(self):
        return self._base_url

    @base_url.setter
    def base_url(self, value):
        self._base_url = value
        self._refresh_client()

    @property
    def timeout(self) -> float:
        return self._timeout

    @timeout.setter
    def timeout(self, value: float):
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError("timeout must be a positive number of seconds.")
        self._timeout = value
        if hasattr(self, "_client"):
            self._refresh_client()

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = ClassificationResult._non_empty_text(value, "model")

    @property
    def prompt_template(self) -> str:
        return self._prompt_template

    @prompt_template.setter
    def prompt_template(self, value: str):
        self._prompt_template = ClassificationResult._non_empty_text(value, "prompt_template")

    @property
    def bin_mapper(self) -> BinMapper:
        return self._bin_mapper

    @bin_mapper.setter
    def bin_mapper(self, value: BinMapper):
        if not isinstance(value, BinMapper):
            raise ValueError("bin_mapper must be a BinMapper.")
        self._bin_mapper = value

    @property
    def client(self):
        return self._client

    # --- Other methods ------------------------------------------------------

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
        unknown = self.bin_mapper.unknown_label
        results = []
        for item in raw.get("items", []):
            name = str(item.get("item_name") or unknown)
            material = str(item.get("material") or unknown)
            pfand = self.bin_mapper.is_pfand(item)
            if pfand:
                bin_type = self.bin_mapper.pfand_bin
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
