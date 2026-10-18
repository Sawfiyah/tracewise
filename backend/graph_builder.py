from falkordb import FalkorDB


def build_project_graph(
    project_id: str,
    analysis: dict,
    host: str = "localhost",
    port: int = 6379,
) -> dict:
    """Store analysed functions and their calls in a FalkorDB graph."""

    db = FalkorDB(host=host, port=port)
    graph = db.select_graph(project_id)

    # Clear this project's graph before rebuilding it.
    graph.query("MATCH (n) DETACH DELETE n")

    # Create one node for each discovered function.
    for function_name in analysis["functions_found"]:
        graph.query(
            """
            CREATE (:Function {name: $name})
            """,
            {"name": function_name},
        )

    # Create relationships for recognised function calls.
    for call in analysis["calls_found"]:
        graph.query(
            """
            MATCH (caller:Function {name: $caller})
            MATCH (callee:Function {name: $callee})
            CREATE (caller)-[:CALLS]->(callee)
            """,
            {
                "caller": call["caller"],
                "callee": call["callee"],
            },
        )

    return {
        "project_id": project_id,
        "functions_stored": len(analysis["functions_found"]),
        "relationships_stored": len(analysis["calls_found"]),
    }