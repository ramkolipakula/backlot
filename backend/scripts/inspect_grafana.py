"""
Inspect Grafana datasources to find correct remote-write endpoints.
Does NOT print secrets.
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GRAFANA_URL = os.getenv("GRAFANA_URL", "")
GRAFANA_TOKEN = os.getenv("GRAFANA_SERVICE_ACCOUNT_TOKEN", "")

def main():
    print(f"Grafana URL: {GRAFANA_URL}")
    print()

    # Query Grafana REST API for all datasources
    resp = requests.get(
        f"{GRAFANA_URL}/api/datasources",
        headers={"Authorization": f"Bearer {GRAFANA_TOKEN}"},
        timeout=15
    )
    print(f"Datasources API status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Error: {resp.text[:500]}")
        return

    datasources = resp.json()
    for ds in datasources:
        name = ds.get("name")
        ds_type = ds.get("type")
        uid = ds.get("uid")
        url = ds.get("url", "")
        print(f"  Datasource: name={name!r}  type={ds_type!r}  uid={uid!r}  url={url!r}")
        jd = ds.get("jsonData", {})
        for k in ("httpMethod", "prometheusType", "prometheusVersion", "timeInterval",
                  "customQueryParameters", "httpHeaderName1"):
            if k in jd:
                print(f"    jsonData.{k}: {jd[k]!r}")

    print()

    # Also check Grafana's own remote write endpoint via the hosted metrics API
    resp2 = requests.get(
        f"{GRAFANA_URL}/api/hosted-metrics/api/v1/remote_write",
        headers={"Authorization": f"Bearer {GRAFANA_TOKEN}"},
        timeout=15
    )
    print(f"Hosted metrics remote_write API status: {resp2.status_code}")
    if resp2.status_code == 200:
        print(resp2.text[:500])

    # Try org info
    resp3 = requests.get(
        f"{GRAFANA_URL}/api/org",
        headers={"Authorization": f"Bearer {GRAFANA_TOKEN}"},
        timeout=15
    )
    print(f"Org API status: {resp3.status_code}")
    if resp3.status_code == 200:
        org = resp3.json()
        print(f"  Org id: {org.get('id')}  name: {org.get('name')!r}")


if __name__ == "__main__":
    main()
