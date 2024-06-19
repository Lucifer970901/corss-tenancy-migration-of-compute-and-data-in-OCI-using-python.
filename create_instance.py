import time
import oci
import json
import pandas as pd
from pandas import json_normalize
import datetime
import os.path
config = oci.config.from_file(file_location="~/.oci/config_sehubjapaciaasset02")


# Initialize service client with default config file
core_client = oci.core.ComputeClient(config)
# Initialize service client with default config file
identity_client = oci.identity.IdentityClient(config)

list_availability_domains_response = identity_client.list_availability_domains(
    compartment_id=config["compartment_id"])

# Get the data from response

try:
    csv_df = pd.read_csv("instance_and_VNIC_details.csv")
    csv_df.dropna()
    i = 0
    print(csv_df)
    for ad in list_availability_domains_response.data:
        Availability_Domain = ad.name
    
    for vm in csv_df.index:
        Instance_name = str(csv_df.iloc[i]["Instance Name"])
        Instance_shape = str(csv_df.iloc[i]["Shape"])
        Image_OCID = str(csv_df.iloc[i]["Custom Image OCID"])
        subnet_OCID = str(csv_df.iloc[i]["subnet OCID"])
        OCPUs = float(csv_df.iloc[i]["OCPUs"])
        Memory_in_gbs = float(csv_df.iloc[i]["Memory in GBs"])
        private_IP = str(csv_df.iloc[i]["Private IP"])
        Boot_Volume_Type = str(csv_df.iloc[i]["boot_volume_type"])
        Network_Type = str(csv_df.iloc[i]["network_type"])
        Remote_Data_Volume_Type = str(csv_df.iloc[i]["remote_data_volume_type"])
        

        launch_instance_response = core_client.launch_instance(
            launch_instance_details=oci.core.models.LaunchInstanceDetails(
            availability_domain=Availability_Domain,
            compartment_id=config["compartment_id"],
            shape = Instance_shape,
            display_name = Instance_name,
            create_vnic_details=oci.core.models.CreateVnicDetails(
            assign_public_ip=True,
            assign_private_dns_record=True,
            private_ip=private_IP,    
            skip_source_dest_check=True,
            subnet_id=subnet_OCID),
            image_id=Image_OCID,
            launch_options=oci.core.models.LaunchOptions(
            boot_volume_type=Boot_Volume_Type,
            firmware="UEFI_64",
            network_type=Network_Type,
            remote_data_volume_type=Remote_Data_Volume_Type,
            is_pv_encryption_in_transit_enabled=True),
            instance_options=oci.core.models.InstanceOptions(
            are_legacy_imds_endpoints_disabled=True),
            availability_config=oci.core.models.LaunchInstanceAvailabilityConfigDetails(
            is_live_migration_preferred=False,
            recovery_action="STOP_INSTANCE"),
            agent_config=oci.core.models.LaunchInstanceAgentConfigDetails(
            is_monitoring_disabled=True,
            is_management_disabled=False,
            are_all_plugins_disabled=True),
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=OCPUs,
            memory_in_gbs=Memory_in_gbs)))
    # Get the data from response
        print(f"Instance launched with OCID: {launch_instance_response.data.id}")
except Exception as e:
        print(e)
        pass

        
        


