"""
backend/mcp/resolver.py — Shared MCP command resolution.

Single authoritative definition of resolve_mcp_grafana_command().
Imported by both backlot_agent.py and approval.py (P2-platform-specific-paths fix).

The Windows-specific fallback logic (USERPROFILE / LOCALAPPDATA probing) is
isolated behind a platform check so non-Windows environments skip it cleanly.
"""
import os
import sys
import shutil


def resolve_mcp_grafana_command():
    """
    Resolve the mcp-grafana launcher command, checking PATH and known fallback locations.

    Returns (command, args) tuple, or (None, []) if not found.

    Resolution order:
      1. MCP_GRAFANA_COMMAND env var (explicit override, cross-platform)
      2. PATH lookup for 'mcp-grafana' directly
      3. PATH lookup for 'uvx' (to invoke 'mcp-grafana' via uvx)
      4. Windows-only: probe known Python Scripts / uv bin directories not always on PATH
    """
    # 1. Explicit env override (highest priority, works on all platforms)
    env_cmd = os.getenv('MCP_GRAFANA_COMMAND')
    if env_cmd:
        parts = env_cmd.split()
        return parts[0], parts[1:]

    # 2. Check PATH for mcp-grafana directly
    mcp_grafana = shutil.which('mcp-grafana')
    if mcp_grafana:
        return mcp_grafana, []

    # 3. Check PATH for uvx
    uvx = shutil.which('uvx')
    if uvx:
        return uvx, ['mcp-grafana']

    # 4. Windows-only: probe known installation directories not always on PATH
    if sys.platform != 'win32':
        return None, []

    import pathlib
    fallback_dirs = []
    userprofile = os.environ.get('USERPROFILE', '')
    localappdata = os.environ.get('LOCALAPPDATA', '')
    if userprofile:
        # pythoncore-3.x-64 style installations
        local_py = pathlib.Path(userprofile) / 'AppData' / 'Local' / 'Python'
        if local_py.is_dir():
            for sub in sorted(local_py.iterdir(), reverse=True):
                fallback_dirs.append(sub / 'Scripts')
        # uv's own bin directory
        fallback_dirs.append(pathlib.Path(userprofile) / 'AppData' / 'Local' / 'uv' / 'bin')
        fallback_dirs.append(pathlib.Path(userprofile) / '.local' / 'bin')
    if localappdata:
        fallback_dirs.append(pathlib.Path(localappdata) / 'uv' / 'bin')

    for d in fallback_dirs:
        for name in ('uvx.exe', 'uvx', 'mcp-grafana.exe', 'mcp-grafana'):
            candidate = d / name
            if candidate.is_file():
                if 'mcp-grafana' in name:
                    return str(candidate), []
                else:  # uvx
                    return str(candidate), ['mcp-grafana']

    return None, []
