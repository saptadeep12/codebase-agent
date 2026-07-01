from langchain_core.tools import tool
import requests
import base64
import fnmatch

GITHUB_API = "https://api.github.com"

# Files/dirs that add noise without adding understanding — skip these entirely
NOISE_PATTERNS = [
    "*.lock", "*.lockb", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "*.min.js", "*.min.css", "*.map",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.ico", "*.webp",
    "*.woff", "*.woff2", "*.ttf", "*.eot",
    "*.pyc", "*.pyo", "__pycache__/*",
    "node_modules/*", ".venv/*", "venv/*", "dist/*", "build/*", ".git/*",
    "*.lock.json", "*.snap",
]

MAX_FILE_CHARS = 6000        # per-file cap before truncation
MAX_TREE_FILES = 150         # cap on file paths returned in tree listing


def _is_noise(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in NOISE_PATTERNS)

def _github_get(url: str, params: dict | None = None) -> dict | list:
    resp = requests.get(url, params=params, headers={"Accept": "application/vnd.github+json"}, timeout=10)
    resp.raise_for_status()
    return resp.json()

@tool
def get_repo_tree(repo: str) -> str:
    """List all files in a GitHub repo. Input: 'owner/reponame'"""
    try:
        meta = _github_get(f"{GITHUB_API}/repos/{repo}")
        branch = meta["default_branch"]
        tree = _github_get(f"{GITHUB_API}/repos/{repo}/git/trees/{branch}?recursive=1")

        files = [
            item["path"] for item in tree["tree"]
            if item["type"] == "blob" and not _is_noise(item["path"])
        ]

        truncated = False
        if len(files) > MAX_TREE_FILES:
            files = files[:MAX_TREE_FILES]
            truncated = True

        result = "\n".join(files)
        if truncated:
            result += f"\n... (truncated — showing {MAX_TREE_FILES} of {len(tree['tree'])} files. Use search_code to find specific files instead of browsing the full tree.)"
        return result
    except Exception as e:
        return f"Error fetching repo tree: {str(e)}"


@tool
def read_file(repo: str, filepath: str, start_line: int = 1, max_lines: int = 200) -> str:
    """Read a file from a GitHub repo, optionally a specific line range for large files.
    Input: repo as 'owner/reponame', filepath as 'src/main.py', start_line (default 1), max_lines (default 200).
    For large files, call this multiple times with increasing start_line to read further sections."""
    try:
        data = _github_get(f"{GITHUB_API}/repos/{repo}/contents/{filepath}")

        if isinstance(data, list):
            return f"'{filepath}' is a directory, not a file. Use get_repo_tree to list its contents."

        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        lines = content.splitlines()
        total_lines = len(lines)

        end_line = min(start_line - 1 + max_lines, total_lines)
        selected = lines[start_line - 1:end_line]
        chunk = "\n".join(selected)

        if len(chunk) > MAX_FILE_CHARS:
            chunk = chunk[:MAX_FILE_CHARS] + "\n... (chunk truncated, character limit reached)"

        header = f"--- {filepath} (lines {start_line}-{end_line} of {total_lines}) ---\n"
        footer = ""
        if end_line < total_lines:
            footer = f"\n... ({total_lines - end_line} more lines. Call read_file again with start_line={end_line + 1} to continue.)"

        return header + chunk + footer
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def search_code(repo: str, keyword: str) -> str:
    """Search for a keyword across files in a GitHub repo. Input: repo as 'owner/reponame', keyword to search."""
    try:
        resp = requests.get(
            f"{GITHUB_API}/search/code",
            params={"q": f"{keyword} repo:{repo}"},
            headers={"Accept": "application/vnd.github+json"}
        )
        data = resp.json()
        if "items" not in data:
            return f"No results or rate limited: {data.get('message', 'unknown error')}"
        results = []
        for item in data["items"][:8]:
            if _is_noise(item["path"]):
                continue
            results.append(f"File: {item['path']}\nURL: {item['html_url']}")
        return "\n\n".join(results) if results else "No matches found."
    except Exception as e:
        return f"Error searching code: {str(e)}"


@tool
def get_repo_info(repo: str) -> str:
    """Get basic metadata about a GitHub repo. Input: 'owner/reponame'"""
    try:
        data = _github_get(f"{GITHUB_API}/repos/{repo}")
        return (
            f"Name: {data['full_name']}\n"
            f"Description: {data.get('description', 'N/A')}\n"
            f"Language: {data.get('language', 'N/A')}\n"
            f"Stars: {data['stargazers_count']}\n"
            f"Open issues: {data['open_issues_count']}\n"
            f"Default branch: {data['default_branch']}"
        )
    except Exception as e:
        return f"Error fetching repo info: {str(e)}"


@tool
def save_answer(filename: str, content: str) -> str:
    """Save the final answer to a markdown file. Input: filename like 'answer.md', content as the full answer."""
    try:
        with open(f"reports/{filename}", "w") as f:
            f.write(content)
        return f"Saved to reports/{filename}"
    except Exception as e:
        return f"Error saving: {str(e)}"