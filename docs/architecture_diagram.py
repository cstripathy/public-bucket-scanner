#!/usr/bin/env python3
"""
Bucket Scanner Architecture Diagram
====================================
Generates a cloud architecture diagram with real provider icons using the
`diagrams` library (https://diagrams.mingrammer.com/).

Requirements:
    pip install diagrams
    apt-get install graphviz   # or: brew install graphviz

Usage:
    python docs/architecture_diagram.py

Output:
    bucket_scanner_architecture.png  (in current working directory)
"""

from diagrams import Cluster, Diagram, Edge

# -- AWS nodes --
from diagrams.aws.storage import S3
from diagrams.aws.network import Route53, CloudFront
from diagrams.aws.compute import EC2, Lambda

# -- GCP nodes --
from diagrams.gcp.storage import Storage as GCS
from diagrams.gcp.network import DNS as CloudDNS

# -- Azure nodes --
from diagrams.azure.storage import BlobStorage

# -- On-premises / generic infrastructure nodes --
from diagrams.onprem.queue import Kafka
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.search import Solr  # stand-in for Elasticsearch
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.network import Nginx, HAProxy
from diagrams.onprem.client import Client
from diagrams.onprem.compute import Server

# -- Generic / programming nodes --
from diagrams.generic.compute import Rack
from diagrams.generic.network import Firewall

# -- Diagram configuration --
GRAPH_ATTR = {
    "fontsize": "28",
    "fontname": "Helvetica",
    "bgcolor": "white",
    "pad": "0.5",
    "nodesep": "0.8",
    "ranksep": "1.2",
    "compound": "true",
}

NODE_ATTR = {
    "fontsize": "11",
    "fontname": "Helvetica",
}

EDGE_ATTR = {
    "fontsize": "10",
    "fontname": "Helvetica",
}


def create_diagram():
    with Diagram(
        "Bucket Scanner - Distributed Architecture",
        filename="bucket_scanner_architecture",
        show=False,
        direction="TB",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        outformat="png",
    ):

        # ------------------------------------------------------------------ #
        #  INPUT LAYER                                                        #
        # ------------------------------------------------------------------ #
        with Cluster("Input Layer"):
            wordlist = Server("Wordlist Engine\nPermutations & Mutations")
            namegen = Server("Name Generator\nML / Pattern-Based")
            feed = Server("Feed Ingestion\nCT Logs / OSINT")

        # ------------------------------------------------------------------ #
        #  MESSAGE QUEUE LAYER                                                #
        # ------------------------------------------------------------------ #
        with Cluster("Message Queue Layer"):
            kafka = Kafka("Kafka\nTarget Queue")
            redis_queue = Redis("Redis Streams\nPriority / Retry")

        # ------------------------------------------------------------------ #
        #  DISTRIBUTED SCANNER WORKERS                                        #
        # ------------------------------------------------------------------ #
        with Cluster("Distributed Scanner Workers"):

            with Cluster("DNS Resolver Pool"):
                dns_resolvers = [
                    Route53("Resolver 1"),
                    Route53("Resolver 2"),
                    Route53("Resolver 3"),
                ]

            with Cluster("HTTP Probe Pool"):
                http_probes = [
                    Nginx("Probe 1"),
                    Nginx("Probe 2"),
                    Nginx("Probe 3"),
                ]

            with Cluster("Object Analyzer"):
                perm_check = Lambda("Permission\nChecker")
                enumerator = Lambda("Content\nEnumerator")
                sensitive = Lambda("Sensitive File\nDetector")

        # ------------------------------------------------------------------ #
        #  NETWORK / RATE CONTROL                                             #
        # ------------------------------------------------------------------ #
        with Cluster("Network & Rate Control"):
            rate_limiter = Firewall("Rate Limiter\nToken Bucket")
            ip_rotation = HAProxy("IP Rotation\nProxy Pool / SOCKS5")

        # ------------------------------------------------------------------ #
        #  TARGET CLOUD PROVIDERS                                             #
        # ------------------------------------------------------------------ #
        with Cluster("Target Cloud Providers"):
            aws_s3 = S3("AWS S3")
            gcp_gcs = GCS("GCP Cloud\nStorage")
            azure_blob = BlobStorage("Azure Blob\nStorage")

        # ------------------------------------------------------------------ #
        #  DATA LAYER                                                         #
        # ------------------------------------------------------------------ #
        with Cluster("Data Layer"):
            postgres = PostgreSQL("PostgreSQL\nResults DB")
            elasticsearch = Solr("Elasticsearch\nSearch Index")
            redis_cache = Redis("Redis\nCache")

        # ------------------------------------------------------------------ #
        #  API & PRESENTATION                                                 #
        # ------------------------------------------------------------------ #
        with Cluster("API & Presentation"):
            api_server = Nginx("REST API\nServer")
            dashboard = Client("Web Dashboard\nReact / Vue")
            notifier = Server("Notifications\nSlack / Webhook")

        # ------------------------------------------------------------------ #
        #  OBSERVABILITY                                                      #
        # ------------------------------------------------------------------ #
        with Cluster("Observability"):
            prom = Prometheus("Prometheus\nMetrics")
            graf = Grafana("Grafana\nDashboards")
            alert = Server("Alertmanager\nPagerDuty")

        # ================================================================== #
        #  EDGES / DATA FLOW                                                  #
        # ================================================================== #

        # Input --> Queue
        wordlist >> Edge(color="darkblue") >> kafka
        namegen >> Edge(color="darkblue") >> kafka
        feed >> Edge(color="darkblue") >> kafka
        kafka >> Edge(label="distribute", color="orange") >> redis_queue

        # Queue --> DNS Resolvers (fan-out)
        for resolver in dns_resolvers:
            redis_queue >> Edge(color="orange") >> resolver

        # DNS --> HTTP Probes
        for i, resolver in enumerate(dns_resolvers):
            resolver >> Edge(color="green") >> http_probes[i]

        # HTTP Probes --> Object Analyzer
        for probe in http_probes:
            probe >> Edge(color="green") >> perm_check

        perm_check >> Edge(color="green") >> enumerator
        enumerator >> Edge(color="green") >> sensitive

        # Workers --> Rate Control --> Cloud
        for probe in http_probes:
            probe >> Edge(style="dashed", color="red", label="throttled") >> rate_limiter

        rate_limiter >> Edge(color="red") >> ip_rotation

        ip_rotation >> Edge(color="gray") >> aws_s3
        ip_rotation >> Edge(color="gray") >> gcp_gcs
        ip_rotation >> Edge(color="gray") >> azure_blob

        # Results --> Data Layer
        sensitive >> Edge(label="findings", color="purple") >> postgres
        sensitive >> Edge(label="index", color="purple") >> elasticsearch
        dns_resolvers[0] >> Edge(style="dashed", label="cache", color="gray") >> redis_cache

        # Data Layer --> API
        postgres >> Edge(color="teal") >> api_server
        elasticsearch >> Edge(color="teal") >> api_server
        api_server >> Edge(color="teal") >> dashboard
        api_server >> Edge(color="teal") >> notifier

        # Monitoring (dashed lines = metrics collection)
        kafka >> Edge(style="dashed", color="goldenrod") >> prom
        redis_queue >> Edge(style="dashed", color="goldenrod") >> prom
        rate_limiter >> Edge(style="dashed", color="goldenrod") >> prom

        prom >> Edge(color="goldenrod") >> graf
        prom >> Edge(color="goldenrod") >> alert


if __name__ == "__main__":
    create_diagram()
    print("Diagram written to: bucket_scanner_architecture.png")
