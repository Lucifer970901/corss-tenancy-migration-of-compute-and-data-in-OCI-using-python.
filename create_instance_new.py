import oci
import pandas as pd

# Load OCI configuration from file
config = oci.config.from_file("~/.oci/config_sehubjapaciaasset02")

# Initialize OCI clients
compute_client = oci.core.ComputeClient(config)
identity_client = oci.identity.IdentityClient(config)

# Function to launch instances
def launch_instance(instance_name, instance_shape, image_ocid, subnet_ocid, ocpus, memory_in_gbs, private_ip, boot_volume_type, network_type, remote_data_volume_type, availability_domain):
    try:
        # Launch instance with provided details
        launch_instance_response = compute_client.launch_instance(
            launch_instance_details=oci.core.models.LaunchInstanceDetails(
                availability_domain=availability_domain,
                compartment_id=config["compartment_id"],
                shape=instance_shape,
                display_name=instance_name,
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    assign_public_ip=True,
                    assign_private_dns_record=True,
                    private_ip=private_ip,
                    skip_source_dest_check=True,
                    subnet_id=subnet_ocid),
                image_id=image_ocid,
                launch_options=oci.core.models.LaunchOptions(
                    boot_volume_type=boot_volume_type,
                    firmware="UEFI_64",
                    network_type=network_type,
                    remote_data_volume_type=remote_data_volume_type,
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
                    ocpus=ocpus,
                    memory_in_gbs=memory_in_gbs)))

        print(f"Instance launched with OCID: {launch_instance_response.data.id}")
        return launch_instance_response.data.id
    
    except oci.exceptions.ServiceError as e:
        print(f"Error launching instance {instance_name}: {e}")
        return None
    

try:
    # Read CSV file into DataFrame
    csv_df = pd.read_csv("instance_and_VNIC_details.csv")

    # Iterate over each row in the DataFrame
    for index, row in csv_df.iterrows():
        instance_name = row["Instance Name"]
        instance_shape = row["Shape"]
        image_ocid = row["Custom Image OCID"]
        subnet_ocid = row["subnet OCID"]
        ocpus = float(row["OCPUs"])
        memory_in_gbs = float(row["Memory in GBs"])
        private_ip = row["Private IP"]
        boot_volume_type = row["boot_volume_type"]
        network_type = row["network_type"]
        remote_data_volume_type = row["remote_data_volume_type"]
        
        # Assuming each row represents a different availability domain
        availability_domain = row["availability domain"]

        # Launch instance with unique details from each row
        instance_id = launch_instance(instance_name, instance_shape, image_ocid, subnet_ocid, ocpus, memory_in_gbs, private_ip, boot_volume_type, network_type, remote_data_volume_type, availability_domain)
        
        if instance_id:
            # Optionally, you can perform further operations here
            pass

except FileNotFoundError:
    print("Error: instance_and_VNIC_details.csv file not found.")

except pd.errors.EmptyDataError:
    print("Error: instance_and_VNIC_details.csv file is empty or could not be read.")

except Exception as e:
    print(f"Unexpected error: {e}")
