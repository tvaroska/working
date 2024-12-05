from typing import Dict
from copy import deepcopy

from langchain_core.prompt_values import ChatPromptValue
from langchain_core.messages import HumanMessage

def flatten_openapi(schema: Dict) -> Dict:
    """
    Flattens an OpenAPI schema by resolving and inlining all references ($ref) in the schema.
    
    This function processes an OpenAPI schema that contains definitions ($defs) and references to those
    definitions. It replaces all references with their actual content, effectively flattening the
    schema structure. The function handles both direct references and references within array items.

    Args:
        schema (Dict): An OpenAPI schema dictionary that may contain $defs and $ref references.
                      The schema should follow OpenAPI/Swagger specification format.
    
    Returns:
        Dict: A flattened version of the input schema where all references are replaced with their
              actual content and the $defs section is removed.
    
    Example:
        Input schema:
        {
            "$defs": {
                "Address": {
                    "properties": {
                        "street": {"type": "string"}
                    }
                }
            },
            "properties": {
                "address": {"$ref": "#/$defs/Address"}
            }
        }
        
        Output schema:
        {
            "properties": {
                "address": {
                    "properties": {
                        "street": {"type": "string"}
                    }
                }
            }
        }
    """
    try:
        defs = {}

        # Cover recursive submodels
        for key, value in schema['$defs'].items():
            replacement = value

            for pkey in value['properties']:
                if '$ref' in value['properties'][pkey]:
                    replacement['properties'][pkey] = defs[value['properties'][pkey]['$ref']]
                elif 'items' in value['properties'][pkey] and '$ref' in value['properties'][pkey]['items']:
                    replacement['properties'][pkey]['items'] = defs[value['properties'][pkey]['items']['$ref']]
            defs[f'#/$defs/{key}'] = replacement
    except KeyError:
        return schema

    for key in schema['properties']:
        # Replace direct ussage of submodel
        if '$ref' in schema['properties'][key]:
            ref = schema['properties'][key]['$ref']
            schema['properties'][key] = defs[ref]
        # Replace list of submodels
        elif 'items' in schema['properties'][key]:
            if '$ref' in schema['properties'][key]['items']:
                ref = schema['properties'][key]['items']['$ref']
                schema['properties'][key]['items'] = defs[ref]

    del schema['$defs']
    return schema


def generate_extract(
    prompt,
    generate_model,
    schema,
    extract_model = None
):
    if isinstance(prompt, str):
        prompt = [HumanMessage(prompt)]
    elif isinstance(prompt, HumanMessage):
        prompt = [prompt]
    elif isinstance(prompt, ChatPromptValue):
        prompt = prompt.messages
    elif isinstance(prompt, list):
        prompt = deepcopy(prompt)
    else:
        raise NotImplementedError

    if extract_model:
        l_extract_model = deepcopy(extract_model)
    else:
        l_extract_model = deepcopy(generate_model)
    l_extract_model = l_extract_model.with_structured_output(
        flatten_openapi(schema.schema()), method='json_mode')

    generated_text = generate_model.invoke(prompt)
    prompt.append(generated_text)
    prompt.append(HumanMessage('Extract informations'))
    structured = l_extract_model.invoke(prompt)

    result = schema.parse_obj(structured)
    
    return (generated_text.content, result)
