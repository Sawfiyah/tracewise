from pathlib import Path

from tree_sitter_language_pack import get_parser


SUPPORTED_EXTENSIONS = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
}

IGNORED_DIRECTORIES = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "coverage",
}


def get_language(file_path: str) -> str | None:
    """Return the parser language for a supported source file."""
    return SUPPORTED_EXTENSIONS.get(Path(file_path).suffix.lower())


def get_function_name(node, source: bytes) -> str | None:
    """Extract a function's name from common JavaScript/TypeScript patterns."""

    if node.type in {
        "function_declaration",
        "generator_function_declaration",
        "method_definition",
    }:
        name_node = node.child_by_field_name("name")

        if name_node:
            return source[name_node.start_byte:name_node.end_byte].decode(
                "utf-8", errors="replace"
            )

    return None


def get_called_name(node, source: bytes) -> str | None:
    """Extract the name of a function being called."""

    function_node = node.child_by_field_name("function")

    if function_node is None:
        return None

    if function_node.type in {"identifier", "property_identifier"}:
        return source[
            function_node.start_byte:function_node.end_byte
        ].decode("utf-8", errors="replace")

    if function_node.type == "member_expression":
        property_node = function_node.child_by_field_name("property")

        if property_node:
            return source[
                property_node.start_byte:property_node.end_byte
            ].decode("utf-8", errors="replace")

    return None


def analyse_file(file_path: str, source_code: str) -> dict:
    """Extract named functions and their function calls from one file."""

    language = get_language(file_path)

    if language is None:
        raise ValueError(f"Unsupported file type: {file_path}")

    parser = get_parser(language)
    source = source_code.encode("utf-8")
    tree = parser.parse(source)

    functions = []
    calls = []

    def walk(node, current_function=None):
        nonlocal functions, calls

        function_name = get_function_name(node, source)

        # Recognise arrow functions and function expressions assigned
        # to variables, e.g. const createOrder = () => {}.
        if node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")

            if (
                name_node
                and value_node
                and value_node.type in {"arrow_function", "function_expression"}
            ):
                function_name = source[
                    name_node.start_byte:name_node.end_byte
                ].decode("utf-8", errors="replace")

        if function_name:
            current_function = function_name

            if function_name not in functions:
                functions.append(function_name)

        if node.type == "call_expression" and current_function:
            called_name = get_called_name(node, source)

            if called_name:
                calls.append({
                    "caller": current_function,
                    "callee": called_name,
                })

        for child in node.children:
            walk(child, current_function)

    walk(tree.root_node)

    return {
        "file": file_path,
        "functions": functions,
        "calls": calls,
        "has_syntax_errors": tree.root_node.has_error,
    }


def analyse_project(files: dict[str, str]) -> dict:
    """Analyse supported source files from an uploaded project."""

    results = []

    for file_path, source_code in files.items():
        path = Path(file_path)

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue

        results.append(analyse_file(file_path, source_code))

    all_functions = set()
    all_calls = []

    for result in results:
        all_functions.update(result["functions"])
        all_calls.extend(result["calls"])

    # Keep only calls whose target matches a function found in the project.
    resolved_calls = [
        call
        for call in all_calls
        if call["callee"] in all_functions
    ]

    return {
        "files_analysed": len(results),
        "functions_found": sorted(all_functions),
        "calls_found": resolved_calls,
        "files": results,
    }