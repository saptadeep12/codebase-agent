from langchain_core.tools import tool
import requests

GITHUB_API = "https://api.github.com"

def _github_get(url: str) -> dict | list:
    resp = requests.get(url, headers={"Accept": "application/vnd.github+json"})
    resp.raise_for_status()
    return resp.json()

@tool
def get_repo_tree(repo: str) -> str:
    """List all files in a GitHub repo. Input: 'owner/reponame'"""
    try:
        # get default branch first
        meta = _github_get(f"{GITHUB_API}/repos/{repo}")
        branch = meta["default_branch"]
        tree = _github_get(f"{GITHUB_API}/repos/{repo}/git/trees/{branch}?recursive=1")
        files = [item["path"] for item in tree["tree"] if item["type"] == "blob"]
        # limit to 200 files to avoid token overflow
        if len(files) > 200:
            files = files[:200]
            files.append("... (truncated, repo has more files)")
        return "\n".join(files)
    except Exception as e:
        return f"Error fetching repo tree: {str(e)}"

@tool
def read_file(repo: str, filepath: str) -> str:
    """Read a file from a GitHub repo. Input: repo as 'owner/reponame', filepath as 'src/main.py'"""
    try:
        data = _github_get(f"{GITHUB_API}/repos/{repo}/contents/{filepath}")
        import base64
        content = base64.b64decode(data["content"]).decode("utf-8")
        # limit to avoid token overflow
        if len(content) > 6000:
            content = content[:6000] + "\n\n... (file truncated)"
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def search_code(repo: str, keyword: str) -> str:
    """Search for a keyword across files in a GitHub repo. Input: repo as 'owner/reponame', keyword to search."""
    try:
        # GitHub code search API
        resp = requests.get(
            f"{GITHUB_API}/search/code",
            params={"q": f"{keyword} repo:{repo}"},
            headers={"Accept": "application/vnd.github+json"}
        )
        data = resp.json()
        if "items" not in data:
            return f"No results or rate limited: {data.get('message', 'unknown error')}"
        results = []
        for item in data["items"][:8]:  # top 8 matches
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