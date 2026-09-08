import asyncio
import os
import shutil
from dotenv import load_dotenv
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

load_dotenv()

def resolve_mcp_grafana_command():
    env_cmd = os.getenv('MCP_GRAFANA_COMMAND')
    if env_cmd:
        parts = env_cmd.split()
        return parts[0], parts[1:]
    mcp_grafana = shutil.which('mcp-grafana')
    if mcp_grafana:
        return mcp_grafana, []
    uvx = shutil.which('uvx')
    if uvx:
        return uvx, ['mcp-grafana']
    return None, []

async def test_mcp():
    cmd, args = resolve_mcp_grafana_command()
    if not cmd:
        print('MCP launcher resolution Command: None Args: [] Executable: MISSING')
        return

    mcp_server_params = StdioServerParameters(
        command=cmd,
        args=args,
        env={
            'GRAFANA_URL': os.getenv('GRAFANA_URL', ''),
            'GRAFANA_SERVICE_ACCOUNT_TOKEN': os.getenv('GRAFANA_SERVICE_ACCOUNT_TOKEN', ''),
            'PATH': os.getenv('PATH', ''),
            'USERPROFILE': os.getenv('USERPROFILE', ''),
            'LOCALAPPDATA': os.getenv('LOCALAPPDATA', ''),
            'SYSTEMROOT': os.getenv('SYSTEMROOT', ''),
        }
    )
    
    try:
        print('Starting uvx mcp-grafana...')
        async with stdio_client(mcp_server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print('Session initialized.')
                
                # Test list_datasources
                result = await session.call_tool('list_datasources', arguments={'limit': 50})
                print('list_datasources successful')
                
                # Test query_prometheus
                print('Testing query_prometheus...')
                prom_res = await session.call_tool('query_prometheus', arguments={
                    'query': 'backlot_tracking_packet_drop_ratio',
                    'start_time': 'now-1h',
                    'end_time': 'now',
                    'datasource_uid': 'grafanacloud-prom'
                })
                raw_text = ''
                for content_item in prom_res.content:
                    if hasattr(content_item, 'text'):
                        raw_text += content_item.text
                print(f'Prometheus backlot_tracking_packet_drop_ratio length: {len(raw_text)}')
                print(f'Contains metric: {"backlot_tracking_packet_drop_ratio" in raw_text}')

                prom_res2 = await session.call_tool('query_prometheus', arguments={
                    'query': 'backlot_dit_ingest_buffer_percent',
                    'start_time': 'now-1h',
                    'end_time': 'now',
                    'datasource_uid': 'grafanacloud-prom'
                })
                raw_text2 = ''
                for content_item in prom_res2.content:
                    if hasattr(content_item, 'text'):
                        raw_text2 += content_item.text
                print(f'Contains metric: {"backlot_dit_ingest_buffer_percent" in raw_text2}')
                
                # Test query_loki_logs
                print('Testing query_loki_logs...')
                loki_res = await session.call_tool('query_loki_logs', arguments={
                    'query': '{job="backlot-synthetic-logs"} |= "frustum"',
                    'start_time': 'now-6h',
                    'end_time': 'now',
                    'limit': 10,
                    'datasource_uid': 'grafanacloud-logs'
                })
                raw_loki = ''
                for content_item in loki_res.content:
                    if hasattr(content_item, 'text'):
                        raw_loki += content_item.text
                print(f'Loki frustum logs length: {len(raw_loki)}')
                print(f'Contains frustum: {"frustum" in raw_loki.lower()}')

    except Exception as e:
        print('Exception during MCP test:', e)

asyncio.run(test_mcp())
