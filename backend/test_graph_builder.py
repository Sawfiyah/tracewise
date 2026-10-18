from analyzer import analyse_project
from graph_builder import build_project_graph
from falkordb import FalkorDB

# Sample project containing two functions.
project = {
    "orders.ts": """
    function checkInventory() {
        return true;
    }

    function createOrder() {
        checkInventory();
    }
    """
}

# Analyse the source code.
analysis = analyse_project(project)

print("=== ANALYSIS ===")
print("Functions:", analysis["functions_found"])
print("Calls:", analysis["calls_found"])

# Store the results in a separate FalkorDB graph.
result = build_project_graph(
    project_id="tracewise_test",
    analysis=analysis,
)

print("\n=== GRAPH BUILDER ===")
print(result)

# Read the stored relationships back from FalkorDB.
db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("tracewise_test")

query_result = graph.query(
    """
    MATCH (caller:Function)-[:CALLS]->(callee:Function)
    RETURN caller.name, callee.name
    """
)

print("\n=== STORED RELATIONSHIPS ===")
for row in query_result.result_set:
    print(f"{row[0]} CALLS {row[1]}")