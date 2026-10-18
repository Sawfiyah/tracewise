from analyzer import analyse_file, analyse_project

# Test 1: Analyse a single TypeScript file
source_code = """
function checkInventory() {
    return true;
}

function createOrder() {
    checkInventory();
}
"""

result = analyse_file("orders.ts", source_code)

print("=== SINGLE FILE TEST ===")
print("Functions:", result["functions"])
print("Calls:", result["calls"])
print("Syntax errors:", result["has_syntax_errors"])

# Test 2: Analyse a project
project = {
    "orders.ts": source_code,
    "notifications.js": """
    function sendConfirmation() {
        console.log("Order confirmed");
    }
    """,
}

project_result = analyse_project(project)

print("\n=== PROJECT TEST ===")
print("Files analysed:", project_result["files_analysed"])
print("Functions found:", project_result["functions_found"])
print("Resolved calls:", project_result["calls_found"])