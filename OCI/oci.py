import argparse
import json
import sys
from diagrams import Diagram, Edge, Node, Cluster
from diagrams.oci.compute import VM
from diagrams.oci.network import Vcn
from diagrams.oci.security import Encryption
from diagrams.oci.storage import BlockStorage, ObjectStorage
from diagrams.oci.database import DatabaseService
from diagrams.generic.compute import Rack
from diagrams.generic.network import Switch, Firewall, Router
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
            resource_name = instance['attributes'].get('display_name', instance['attributes'].get('name', resource['name']))
            resource_id = f"{resource_type}.{resource_name}"
            resources[resource_id] = {
                'type': resource_type,
                'name': resource_name,
                'attributes': instance['attributes']
            }
    
    return resources

def map_resource_to_icon(resource_type):
    oci_mappings = {
        'oci_core_instance': VM,
        'oci_core_vcn': Vcn,
        'oci_core_subnet': Switch,
        'oci_core_security_list': Firewall,
        'oci_core_route_table': Router,
        'oci_core_nat_gateway': Router,
        'oci_core_internet_gateway': Router,
        'oci_core_service_gateway': Router,
        'oci_core_volume': BlockStorage,
        'oci_objectstorage_bucket': ObjectStorage,
        'oci_database_db_system': DatabaseService,
        'oci_core_network_security_group': Firewall,
        'oci_core_network_security_group_security_rule': Firewall,
    }
    
    return oci_mappings.get(resource_type, Datacenter)

def generate_diagram(resources, output_file):
    graph_attr = {
        "fontsize": "45",
        "bgcolor": "white" #I like transparent more but this works better for attaching
    }
    node_attr = {
        "fontsize": "14"
    }
    edge_attr = {
        "color": "#00A86B",
        "penwidth": "2"
    }

    with Diagram("OCI Infrastructure", show=False, filename=output_file, direction="TB", graph_attr=graph_attr, node_attr=node_attr, edge_attr=edge_attr):
        nodes = {}
        connections = {resource_id: set() for resource_id in resources}

        # Create all nodes
        for resource_id, resource in resources.items():
            icon_class = map_resource_to_icon(resource['type'])
            nodes[resource_id] = icon_class(resource['name'])

        # Create connections
        for resource_id, resource in resources.items():
            attrs = resource['attributes']
            
            if resource['type'] == 'oci_core_instance':
                subnet_id = attrs.get('subnet_id')
                if subnet_id:
                    for other_id in resources:
                        if resources[other_id]['type'] == 'oci_core_subnet' and resources[other_id]['attributes'].get('id') == subnet_id:
                            connections[resource_id].add(other_id)
                            connections[other_id].add(resource_id)
                
                # Connect instance to its NSG
                for other_id, other_resource in resources.items():
                    if other_resource['type'] == 'oci_core_network_security_group':
                        connections[resource_id].add(other_id)
                        connections[other_id].add(resource_id)

            elif resource['type'] == 'oci_core_subnet':
                vcn_id = attrs.get('vcn_id')
                if vcn_id:
                    for other_id in resources:
                        if resources[other_id]['type'] == 'oci_core_vcn' and resources[other_id]['attributes'].get('id') == vcn_id:
                            connections[resource_id].add(other_id)
                            connections[other_id].add(resource_id)

            elif resource['type'] in ['oci_core_security_list', 'oci_core_route_table', 'oci_core_nat_gateway', 'oci_core_internet_gateway', 'oci_core_service_gateway']:
                vcn_id = attrs.get('vcn_id')
                if vcn_id:
                    for other_id in resources:
                        if resources[other_id]['type'] == 'oci_core_vcn' and resources[other_id]['attributes'].get('id') == vcn_id:
                            connections[resource_id].add(other_id)
                            connections[other_id].add(resource_id)

            elif resource['type'] == 'oci_core_network_security_group':
                vcn_id = attrs.get('vcn_id')
                if vcn_id:
                    for other_id in resources:
                        if resources[other_id]['type'] == 'oci_core_vcn' and resources[other_id]['attributes'].get('id') == vcn_id:
                            connections[resource_id].add(other_id)
                            connections[other_id].add(resource_id)
                
                # Connect NSG to instances
                for other_id, other_resource in resources.items():
                    if other_resource['type'] == 'oci_core_instance':
                        connections[resource_id].add(other_id)
                        connections[other_id].add(resource_id)

            elif resource['type'] == 'oci_core_network_security_group_security_rule':
                nsg_id = attrs.get('network_security_group_id')
                if nsg_id:
                    for other_id in resources:
                        if resources[other_id]['type'] == 'oci_core_network_security_group' and resources[other_id]['attributes'].get('id') == nsg_id:
                            connections[resource_id].add(other_id)
                            connections[other_id].add(resource_id)

            # Connect all resources to their compartment
            compartment_id = attrs.get('compartment_id')
            if compartment_id:
                for other_id in resources:
                    if resources[other_id]['type'] == 'oci_identity_compartment' and resources[other_id]['attributes'].get('id') == compartment_id:
                        connections[resource_id].add(other_id)
                        connections[other_id].add(resource_id)

        # Draw connections
        for source_id, target_ids in connections.items():
            for target_id in target_ids:
                if source_id in nodes and target_id in nodes and source_id != target_id:
                    nodes[source_id] >> nodes[target_id]

def main():
    parser = argparse.ArgumentParser(description="Generate infrastructure diagram from Terraform state")
    parser.add_argument("--state", required=True, help="Path to Terraform state file")
    parser.add_argument("--output", default="oci_infrastructure_diagram", help="Output file name (without extension)")
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