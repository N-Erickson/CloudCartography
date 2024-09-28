import argparse
import json
import sys
from diagrams import Diagram, Edge, Node, Cluster
from diagrams.gcp.compute import ComputeEngine
from diagrams.gcp.network import VirtualPrivateCloud, Router, NAT, FirewallRules, Routes
from diagrams.gcp.storage import Storage
from diagrams.gcp.database import SQL
from diagrams.gcp.analytics import Bigquery
from diagrams.gcp.security import Iam, ResourceManager
from diagrams.generic.network import Subnet  # For subnets
from diagrams.generic.compute import Rack
from diagrams.generic.storage import Storage as GenericStorage
from diagrams.generic.database import SQL as GenericSQL
from diagrams.generic.place import Datacenter

def parse_terraform_state(state_file):
    with open(state_file, 'r') as f:
        state_data = json.load(f)
    
    resources = {}
    for resource in state_data['resources']:
        resource_type = resource['type']
        for instance in resource['instances']:
            resource_name = instance['attributes'].get('name', resource['name'])
            resource_id = f"{resource_type}.{resource_name}"
            resources[resource_id] = {
                'type': resource_type,
                'name': resource_name,
                'attributes': instance['attributes']
            }
    
    return resources

def map_resource_to_icon(resource_type):
    # Correct mapping of Terraform resource types to diagram classes
    gcp_mappings = {
        'google_compute_instance': ComputeEngine,
        'google_compute_network': VirtualPrivateCloud,  
        'google_compute_subnetwork': Subnet,  # Generic Subnet icon for GCP
        'google_compute_firewall': FirewallRules,
        'google_compute_router': Router,
        'google_compute_router_nat': NAT,
        'google_storage_bucket': Storage,
        'google_sql_database_instance': SQL,
        'google_bigquery_dataset': Bigquery,
        'google_iam_policy': Iam,
        'google_compute_route': Routes,
        'google_project': ResourceManager
    }
    
    if resource_type in gcp_mappings:
        return gcp_mappings[resource_type]
    else:
        # Generic mappings for any unmatched resource types
        if 'compute' in resource_type:
            return Rack
        elif 'network' in resource_type:
            return Switch
        elif 'storage' in resource_type:
            return GenericStorage
        elif 'database' in resource_type:
            return GenericSQL
        elif 'security' in resource_type or 'iam' in resource_type:
            return Iam
        elif 'project' in resource_type or 'resource_manager' in resource_type:
            return ResourceManager
        else:
            return Datacenter

def generate_diagram(resources, output_file):
    graph_attr = {
        "fontsize": "45",
        "bgcolor": "transparent"
    }
    node_attr = {
        "fontsize": "14"
    }
    edge_attr = {
        "color": "#00A86B",
        "penwidth": "2"
    }

    with Diagram("GCP Infrastructure", show=False, filename=output_file, direction="TB", graph_attr=graph_attr, node_attr=node_attr, edge_attr=edge_attr):
        nodes = {}
        connections = {}

        # Create all nodes
        for resource_id, resource in resources.items():
            icon_class = map_resource_to_icon(resource['type'])
            nodes[resource_id] = icon_class(resource['name'])

        # Create connections
        for resource_id, resource in resources.items():
            connections[resource_id] = set()

            # Common attribute connections
            for attr, value in resource['attributes'].items():
                if isinstance(value, str):
                    for other_id, other_resource in resources.items():
                        if other_resource['name'] in value and other_id != resource_id:
                            connections[resource_id].add(other_id)

            # Specific resource type connections
            if resource['type'] == 'google_compute_instance':
                subnet_id = resource['attributes'].get('subnetwork', '').split('/')[-1]
                network_id = resource['attributes'].get('network', '').split('/')[-1]
                for other_id, other_resource in resources.items():
                    if other_id != resource_id:
                        if other_resource['type'] == 'google_compute_subnetwork' and other_resource['name'] == subnet_id:
                            connections[resource_id].add(other_id)
                            connections[other_id].add(resource_id)  # Bidirectional connection
                        if other_resource['type'] == 'google_compute_network' and other_resource['name'] == network_id:
                            connections[resource_id].add(other_id)

            elif resource['type'] == 'google_compute_subnetwork':
                network_id = resource['attributes'].get('network', '').split('/')[-1]
                for other_id, other_resource in resources.items():
                    if other_id != resource_id:
                        if other_resource['type'] == 'google_compute_network' and other_resource['name'] == network_id:
                            connections[resource_id].add(other_id)
                        if other_resource['type'] == 'google_compute_instance' and resource['name'] in other_resource['attributes'].get('subnetwork', ''):
                            connections[resource_id].add(other_id)

            elif resource['type'] == 'google_compute_firewall':
                network_id = resource['attributes'].get('network', '').split('/')[-1]
                for other_id, other_resource in resources.items():
                    if other_id != resource_id:
                        if other_resource['type'] == 'google_compute_network' and other_resource['name'] == network_id:
                            connections[resource_id].add(other_id)
                        if other_resource['type'] == 'google_compute_instance':
                            connections[resource_id].add(other_id)

            elif resource['type'] == 'google_compute_router':
                network_id = resource['attributes'].get('network', '').split('/')[-1]
                for other_id, other_resource in resources.items():
                    if other_id != resource_id:
                        if other_resource['type'] == 'google_compute_network' and other_resource['name'] == network_id:
                            connections[resource_id].add(other_id)

            elif resource['type'] == 'google_compute_router_nat':
                router_name = resource['attributes'].get('router', '')
                for other_id, other_resource in resources.items():
                    if other_id != resource_id:
                        if other_resource['type'] == 'google_compute_router' and other_resource['name'] == router_name:
                            connections[resource_id].add(other_id)

        # Draw connections
        for source_id, target_ids in connections.items():
            for target_id in target_ids:
                if source_id in nodes and target_id in nodes and source_id != target_id:
                    nodes[source_id] >> nodes[target_id]

def main():
    parser = argparse.ArgumentParser(description="Generate infrastructure diagram from Terraform state")
    parser.add_argument("--state", required=True, help="Path to Terraform state file")
    parser.add_argument("--output", default="infrastructure_diagram", help="Output file name (without extension)")
    args = parser.parse_args()

    try:
        resources = parse_terraform_state(args.state)
        generate_diagram(resources, args.output)
        print(f"Infrastructure diagram generated successfully! Saved as {args.output}.png")
    except Exception as e:
        print(f"An error occurred: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
