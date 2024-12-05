import pytest
from .utils import flatten_openapi

FLATTEN_TEST_CASES = [
    (
        "basic_reference",
        {
            "$defs": {
                "Address": {
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"}
                    }
                }
            },
            "properties": {
                "address": {"$ref": "#/$defs/Address"}
            }
        },
        {
            "properties": {
                "address": {
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"}
                    }
                }
            }
        }
    ),
    (
        "array_reference",
        {
            "$defs": {
                "Tag": {
                    "properties": {
                        "name": {"type": "string"}
                    }
                }
            },
            "properties": {
                "tags": {
                    "items": {"$ref": "#/$defs/Tag"},
                    "type": "array"
                }
            }
        },
        {
            "properties": {
                "tags": {
                    "items": {
                        "properties": {
                            "name": {"type": "string"}
                        }
                    },
                    "type": "array"
                }
            }
        }
    ),
    (
        "nested_reference",
        {
            "$defs": {
                "Address": {
                    "properties": {
                        "street": {"type": "string"},
                        "country": {"$ref": "#/$defs/Country"}
                    }
                },
                "Country": {
                    "properties": {
                        "name": {"type": "string"},
                        "code": {"type": "string"}
                    }
                }
            },
            "properties": {
                "address": {"$ref": "#/$defs/Address"}
            }
        },
        {
            "properties": {
                "address": {
                    "properties": {
                        "street": {"type": "string"},
                        "country": {
                            "properties": {
                                "name": {"type": "string"},
                                "code": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    ),
    (
        "no_references",
        {
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        },
        {
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        }
    ),
    (
        "empty_schema",
        {},
        {}
    ),
    (
        "empty_defs",
        {
            "$defs": {},
            "properties": {
                "name": {"type": "string"}
            }
        },
        {
            "properties": {
                "name": {"type": "string"}
            }
        }
    )
]

@pytest.mark.parametrize("test_id, input_schema, expected", FLATTEN_TEST_CASES)
def test_flatten_openapi(test_id, input_schema, expected):
    """
    Test flatten_openapi function with various schema structures.
    
    Parameters:
        test_id: Identifier for the test case
        input_schema: Input OpenAPI schema to flatten
        expected: Expected output after flattening
    """
    result = flatten_openapi(input_schema)
    assert result == expected
