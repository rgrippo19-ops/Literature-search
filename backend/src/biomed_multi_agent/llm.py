from __future__ import annotations

import json
from typing import Any, Type

from openai import OpenAI
from pydantic import BaseModel

from .config import SETTINGS


def _normalize_openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively normalize a Pydantic JSON schema into the stricter form
    expected by OpenAI structured outputs.

    Rules:
    - every object schema gets additionalProperties=false
    - every object schema gets required=[all property names]
    """
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            properties = schema.get("properties", {})
            if isinstance(properties, dict):
                schema["required"] = list(properties.keys())
            schema["additionalProperties"] = False

        for key in ("properties", "$defs", "definitions"):
            value = schema.get(key)
            if isinstance(value, dict):
                for subkey, subschema in value.items():
                    value[subkey] = _normalize_openai_schema(subschema)

        if "items" in schema and isinstance(schema["items"], dict):
            schema["items"] = _normalize_openai_schema(schema["items"])

        for key in ("anyOf", "oneOf", "allOf"):
            if key in schema and isinstance(schema[key], list):
                schema[key] = [_normalize_openai_schema(item) for item in schema[key]]

    return schema


class LLMClient:
    def __init__(self) -> None:
        self._client = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not SETTINGS.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required before making model calls.")
            self._client = OpenAI(
                api_key=SETTINGS.openai_api_key,
                timeout=SETTINGS.openai_timeout_sec,
                max_retries=SETTINGS.openai_max_retries,
            )
        return self._client

    def generate_model(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema_model: Type[BaseModel],
    ) -> BaseModel:
        schema = schema_model.model_json_schema()
        schema = _normalize_openai_schema(schema)

        response = self.client.responses.create(
            model=model,
            reasoning={"effort": SETTINGS.openai_reasoning_effort},
            store=SETTINGS.openai_store,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_model.__name__,
                    "schema": schema,
                    "strict": True,
                }
            },
        )

        payload = json.loads(response.output_text)
        return schema_model.model_validate(payload)

    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema_model: Type[BaseModel],
    ) -> dict[str, Any]:
        return self.generate_model(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_model=schema_model,
        ).model_dump()

    def generate_text(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        response = self.client.responses.create(
            model=model,
            reasoning={"effort": SETTINGS.openai_reasoning_effort},
            store=SETTINGS.openai_store,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
        )
        return response.output_text


LLM = LLMClient()