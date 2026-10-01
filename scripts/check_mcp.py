#!/usr/bin/env python3
"""Official SDK stdio semantic checks. No installed third-party client is certified."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
import tempfile

from seedlib.common import dump
from seedlib.context import Context, build

TOOLS = {'context_status', 'search_codebase', 'find_symbol', 'related_context',
         'read_source', 'planning_handoff'}


def fixture(root: Path) -> None:
    """Synthetic, credential-free evidence for exact protocol assertions."""
    files = {
        'README.md': '# Semantic fixture\n\n## Login\nAuthenticate an approved local user.\n',
        'src/api.py': 'def login(user):\n    return user\n' + '# spacer\n' * 90 + 'CONTRACT_MARKER = 42\n',
        'tests/test_api.py': 'def test_login():\n    assert True\n',
        'large.json': json.dumps({'text': 'bounded-source-' * 3000}),
        '.seed/context-links.json': dump([
            {'source': 'README.md#section:Login', 'target': 'src/api.py#symbol:login', 'relation': 'documents'},
            {'source': 'tests/test_api.py', 'target': 'src/api.py', 'relation': 'tests'}]),
    }
    for name, value in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding='utf-8')
    build(root)


def payload(result) -> dict:
    if result.isError:
        raise RuntimeError('MCP tool reported an error')
    structured = getattr(result, 'structuredContent', None)
    if isinstance(structured, dict):
        return structured
    for part in result.content:
        if getattr(part, 'type', None) == 'text':
            value = json.loads(part.text)
            if isinstance(value, dict):
                return value
    raise RuntimeError('MCP tool did not return the expected object')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


async def exercise(session, root: Path) -> list[str]:
    """Assertions are about evidence contents, not merely isError=false."""
    observations = []
    async def call(name, args=None):
        return payload(await session.call_tool(name, args or {}))

    names = {tool.name for tool in (await session.list_tools()).tools}
    require(names == TOOLS, 'Unexpected tool surface')
    require((await call('context_status'))['status'] == 'FRESH', 'Fresh index expected')
    found = await call('find_symbol', {'name': 'login'})
    require(any(item['path'] == 'src/api.py' and item['start'] == 1 for item in found['items']),
            'Exact Python symbol/source span not found')
    symbol = next(item['id'] for item in found['items'] if item['path'] == 'src/api.py')
    relations = await call('related_context', {'target': symbol})
    require(any(edge['kind'] == 'documents' for edge in relations['edges']), 'Document/symbol relationship missing')
    relations = await call('related_context', {'target': 'src/api.py'})
    require(any(edge['kind'] == 'tests' and edge['src'] == 'tests/test_api.py' for edge in relations['edges']),
            'Declared test relationship missing')
    search = await call('search_codebase', {'query': 'CONTRACT_MARKER'})
    require(any('CONTRACT_MARKER' in item['excerpt'] for item in search['items']), 'Top-level source coverage missing')
    source = await call('read_source', {'path': 'src/api.py', 'start': 1, 'end': 2})
    require(source['content'] == 'def login(user):\n    return user\n', 'Source content differs')
    require(source['source_sha256'] in source['provenance'], 'Source provenance missing')
    observations += ['tool-surface', 'exact-symbol', 'declared-doc-and-test-edges', 'module-level-search', 'exact-source']

    page = await call('read_source', {'path': 'large.json', 'start': 1, 'end': 1, 'max_chars': 2000})
    require(page['truncated'] and len(dump(page)) <= 2000, 'Source response budget not respected')
    second = await call('read_source', page['continuation'])
    require(second['content_offset_chars'] == len(page['content']), 'Read continuation skipped/repeated content')
    require(second['source_sha256'] == page['source_sha256'], 'Continuation changed revision')
    observations.append('bounded-continuation')
    require((await call('planning_handoff'))['status'] == 'NOT_CONFIGURED', 'Optional planner incorrectly required')
    observations.append('optional-planner')
    rejected = await session.call_tool('read_source', {'path': '../outside'})
    require(rejected.isError, 'Traversal not rejected')
    observations.append('traversal-rejection')
    (root / 'src/api.py').write_text('def replacement():\n    return 0\n', encoding='utf-8')
    require((await call('context_status'))['status'] == 'STALE', 'Mutation did not stale index')
    require((await session.call_tool('find_symbol', {'name': 'login'})).isError, 'Stale index returned evidence')
    observations.append('stale-evidence-rejection')
    return observations


async def check(root: Path) -> dict:
    # Import first: no alternative protocol or fake transport on dependency failure.
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    root = root.resolve()
    require(Context(root).status()['status'] == 'FRESH', 'Index the actual checkout before protocol verification')
    script = str(Path(__file__).with_name('seed_mcp.py').resolve())
    # Check real checkout freshness across the transport as well as isolated fixtures.
    async with asyncio.timeout(90):
        params = StdioServerParameters(command=sys.executable, args=[script, '--root', str(root)])
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                require(payload(await session.call_tool('context_status', {}))['status'] == 'FRESH',
                        'Real checkout differs across MCP transport')
        with tempfile.TemporaryDirectory(prefix='seed-mcp-semantic-') as directory:
            sample = Path(directory).resolve()
            fixture(sample)
            params = StdioServerParameters(command=sys.executable, args=[script, '--root', str(sample)])
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    observations = await exercise(session, sample)
    return {'status': 'PASS', 'observations': observations,
            'scope': 'Official SDK stdio and synthetic evidence semantics; no Claude/Codex/Cursor UI or application certified.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(check(args.root)), indent=2))
    except ImportError:
        print('BLOCKED: official MCP SDK is not installed', file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        print('FAIL: ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
