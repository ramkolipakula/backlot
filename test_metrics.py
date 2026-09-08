import asyncio, os, shutil, json
from dotenv import load_dotenv
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

load_dotenv()
cmd, args = shutil.which('uvx'), ['mcp-grafana']
async def test_mcp():
    mcp_server_params = StdioServerParameters(
        command=cmd, args=args,
        env={'GRAFANA_URL': os.getenv('GRAFANA_URL', ''), 'GRAFANA_SERVICE_ACCOUNT_TOKEN': os.getenv('GRAFANA_SERVICE_ACCOUNT_TOKEN', ''), 'PATH': os.getenv('PATH', '')}
    )
    
    async with stdio_client(mcp_server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            res = await session.call_tool('query_prometheus', arguments={
                'expr': 'backlot_tracking_packet_drop_ratio', 
                'startTime': 'now-30d', 
                'endTime': 'now', 
                'queryType': 'range',
                'stepSeconds': 3600,
                'datasourceUid': 'grafanacloud-prom'
            })
            raw1 = ''.join(c.text for c in res.content if hasattr(c, 'text'))
            print('PROM1:', raw1[:200])

asyncio.run(test_mcp())
