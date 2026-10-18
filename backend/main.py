import io
import uuid
import zipfile
from pathlib import PurePosixPath

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from falkordb import FalkorDB

from analyzer import analyse_project
from graph_builder import build_project_graph

app = FastAPI(
    title="TraceWise API",
    description="Graph-powered code impact analysis.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("tracewise")


class ImpactRequest(BaseModel):
    function_name: str
    project_id: str = "tracewise"


class ProjectAnalysisRequest(BaseModel):
    project_id: str
    files: dict[str, str]


@app.get("/")
def home():
    return {"message": "TraceWise API is running!"}


@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/projects/upload")
async def upload_project(file: UploadFile = File(...)):
    """Upload a ZIP project, analyse supported files, and build its graph."""

    MAX_ARCHIVE_SIZE = 20 * 1024 * 1024  # 20 MB
    MAX_TOTAL_SIZE = 100 * 1024 * 1024   # 100 MB uncompressed
    MAX_FILES = 500

    supported_extensions = {".js", ".jsx", ".ts", ".tsx"}
    ignored_directories = {
        "node_modules",
        ".git",
        "dist",
        "build",
        ".next",
        "coverage",
    }

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a ZIP file.",
        )

    try:
        archive_bytes = await file.read(MAX_ARCHIVE_SIZE + 1)

        if len(archive_bytes) > MAX_ARCHIVE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="The ZIP file exceeds the 20 MB upload limit.",
            )

        files = {}

        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            entries = archive.infolist()

            if len(entries) > MAX_FILES:
                raise HTTPException(
                    status_code=413,
                    detail=f"The archive contains too many entries. Maximum: {MAX_FILES}.",
                )

            total_size = sum(entry.file_size for entry in entries)

            if total_size > MAX_TOTAL_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="The uncompressed archive exceeds the 100 MB limit.",
                )

            for entry in entries:
                if entry.is_dir():
                    continue

                path = PurePosixPath(entry.filename)

                # Reject absolute paths and directory traversal attempts.
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in entry.filename
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="The ZIP contains an unsafe file path.",
                    )

                if any(part in ignored_directories for part in path.parts):
                    continue

                if path.suffix.lower() not in supported_extensions:
                    continue

                # Avoid parsing oversized individual source files.
                if entry.file_size > 2 * 1024 * 1024:
                    continue

                try:
                    with archive.open(entry) as source_file:
                        source_code = source_file.read().decode("utf-8")
                except UnicodeDecodeError:
                    continue

                files[path.as_posix()] = source_code

        if not files:
            raise HTTPException(
                status_code=400,
                detail="No supported JavaScript or TypeScript files were found.",
            )

        analysis = analyse_project(files)

        if not analysis["functions_found"]:
            raise HTTPException(
                status_code=400,
                detail="No supported functions were found in the uploaded project.",
            )

        # Generate a server-controlled graph name for isolation.
        project_id = f"project_{uuid.uuid4().hex}"

        result = build_project_graph(
            project_id=project_id,
            analysis=analysis,
        )

        return {
            **result,
            "files_analysed": analysis["files_analysed"],
            "functions_found": analysis["functions_found"],
            "calls_found": analysis["calls_found"],
            "message": "Project uploaded and analysed successfully.",
        }

    except HTTPException:
        raise
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid ZIP archive.",
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Project upload failed: {str(error)}",
        )
    finally:
        await file.close()

@app.post("/projects/analyze")
def analyze_project_endpoint(request: ProjectAnalysisRequest):
    """Analyse source files and store their relationships in FalkorDB."""

    if not request.files:
        raise HTTPException(
            status_code=400,
            detail="Please provide at least one source file.",
        )

    try:
        analysis = analyse_project(request.files)

        if not analysis["functions_found"]:
            raise HTTPException(
                status_code=400,
                detail="No supported functions were found in the provided files.",
            )

        result = build_project_graph(
            project_id=request.project_id,
            analysis=analysis,
        )

        return {
            **result,
            "files_analysed": analysis["files_analysed"],
            "functions_found": analysis["functions_found"],
            "calls_found": analysis["calls_found"],
            "message": "Project analysed and graph created successfully.",
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Project analysis failed: {str(error)}",
        )


@app.post("/impact")
def analyze_impact(request: ImpactRequest):
    try:
        if not request.project_id.replace("_", "").isalnum():
            raise HTTPException(
                status_code=400,
                detail="Invalid project ID.",
            )

        project_graph = db.select_graph(request.project_id)

        result = project_graph.query(
            """
            MATCH (changed:Function {name: $function_name})
            OPTIONAL MATCH (dependent:Function)-[:CALLS*1..5]->(changed)
            WITH changed, collect(DISTINCT dependent.name) AS affected
            RETURN changed.name AS changed_function,
                   affected AS affected_components
            """,
            {"function_name": request.function_name},
        )

        if not result.result_set:
            raise HTTPException(
                status_code=404,
                detail=f"Function '{request.function_name}' was not found.",
            )

        row = result.result_set[0]

        return {
            "changed_function": row[0],
            "affected_components": [
                name for name in (row[1] or []) if name is not None
            ],
            "related_tests": [],
            "message": "Impact analysis completed successfully.",
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Impact analysis failed: {str(error)}",
        )
        
@app.get("/projects/{project_id}/graph")
def get_project_graph(project_id: str):
    """Return the nodes and relationships stored in a project's graph."""

    if not project_id.replace("_", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID.",
        )

    try:
        project_graph = db.select_graph(project_id)

        result = project_graph.query(
            """
            MATCH (source:Function)-[relationship:CALLS]->(target:Function)
            RETURN source.name AS source,
                   target.name AS target,
                   type(relationship) AS relationship_type
            """
        )

        edges = []
        node_names = set()

        for row in result.result_set:
            source = row[0]
            target = row[1]
            relationship_type = row[2]

            node_names.add(source)
            node_names.add(target)

            edges.append({
                "source": source,
                "target": target,
                "type": relationship_type,
            })

        # Also retrieve functions that have no outgoing CALLS relationships.
        nodes_result = project_graph.query(
            """
            MATCH (function:Function)
            RETURN function.name AS name
            """
        )

        for row in nodes_result.result_set:
            node_names.add(row[0])

        nodes = [
            {
                "id": name,
                "label": name,
                "type": "Function",
            }
            for name in sorted(node_names)
        ]

        return {
            "project_id": project_id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve project graph: {str(error)}",
        )