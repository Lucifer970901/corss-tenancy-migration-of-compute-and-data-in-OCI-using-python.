import oci
import json
import pandas as pd
from pandas import json_normalize
import datetime
import time
import concurrent.futures

# Load OCI configuration
config = oci.config.from_file(file_location="~/.oci/config_sehubjapaciaasset01")

# Initialize OCI clients
compute_client = oci.core.ComputeClient(config)
object_storage_client = oci.object_storage.ObjectStorageClient(config)
block_storage_client = oci.core.BlockstorageClient(config)
network_client = oci.core.VirtualNetworkClient(config)

# Initialize bucket name
bucket_name = "image_backup"

# Get namespace dynamically
get_namespace_response = object_storage_client.get_namespace(compartment_id=config["compartment_id"])
print("Namespace:", get_namespace_response.data)

# Initialize lists to store details
image_lst = []
backup_lst = []
file_lst = []

# Read the instances CSV file
csv_df = pd.read_csv("list_instances.csv")

if csv_df.empty:
    print("The CSV file is empty.")
else:
    print("CSV Data:")
    print(csv_df)

# Process each instance
for i in csv_df.index:
    compute_id = str(csv_df.iloc[i]["Instance OCID"])
    print(f"Processing instance with OCID: {compute_id}")

    # Reset lists for each instance
    vnic_lst = []
    subnet_lst = []
    ip_lst = []

    # Get VNIC details for the instance
    list_vnic_attachments_response = compute_client.list_vnic_attachments(compartment_id=config["compartment_id"])

    for a in list_vnic_attachments_response.data:
        if compute_id == a.instance_id:
            vnic_lst.append(a.vnic_id)
            subnet_lst.append(a.subnet_id)
            print(f"VNIC ID: {a.vnic_id}, Subnet ID: {a.subnet_id}")

    # Get IP addresses for each VNIC
    for b in vnic_lst:
        list_private_ips_response = network_client.list_private_ips(vnic_id=str(b))
        for c in list_private_ips_response.data:
            ip_lst.append(c.ip_address)
            print(f"Instance OCID: {compute_id}, VNIC ID: {b}, Private IP: {c.ip_address}")

    # Get instance details
    get_instance_response = compute_client.get_instance(compute_id)
    instance = get_instance_response.data

    # Create a custom image for the instance
    try:
        create_image_response = compute_client.create_image(
            create_image_details=oci.core.models.CreateImageDetails(
                compartment_id=config["compartment_id"],
                instance_id=instance.id,
                display_name=instance.display_name,
                launch_mode="NATIVE"
            )
        )
        image_lst.append(create_image_response.data.id)

        # Store instance and VNIC details
        file_lst.append([
            instance.id,
            instance.display_name,
            instance.shape,
            instance.shape_config.ocpus,
            instance.shape_config.memory_in_gbs,
            ip_lst,  # List of IPs
            create_image_response.data.id,
            subnet_lst,  # List of subnets
            instance.availability_domain,
            instance.launch_options.boot_volume_type,
            instance.launch_options.network_type,
            instance.launch_options.remote_data_volume_type
        ])
        print(f"Custom image created for instance {instance.display_name}: {create_image_response.data.id}")

    except Exception as e:
        print(f"Error processing instance {instance.display_name}: {e}")

# Save the details to a CSV file
df = pd.DataFrame(file_lst, columns=[
    "Instance_OCID", "Instance Name", "Shape", "OCPUs", "Memory in GBs", 
    "Private IPs", "Custom Image OCID", "Subnets", "Availability Domain",
    "Boot Volume Type", "Network Type", "Remote Data Volume Type"
])
df = df.dropna()
df.to_csv("instance_and_VNIC_details.csv", index=False)
print("Instance and VNIC details saved to CSV.")
print(df)

# Check if the bucket exists
def bucket_exists(bucket_name):
    try:
        object_storage_client.get_bucket(namespace_name=get_namespace_response.data, bucket_name=bucket_name)
        return True
    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            return False  # Bucket does not exist
        else:
            raise e  # Other error

# Create the bucket if it does not exist
if not bucket_exists(bucket_name):
    create_bucket_request = oci.object_storage.models.CreateBucketDetails(
        compartment_id=config["compartment_id"],
        name=bucket_name,
        public_access_type="NoPublicAccess",
        storage_tier="Standard",
        object_events_enabled=False,
        versioning="Enabled",
        auto_tiering="Disabled"
    )

    try:
        object_storage_client.create_bucket(namespace_name=get_namespace_response.data, create_bucket_details=create_bucket_request)
        print(f"Bucket '{bucket_name}' created successfully.")
    except oci.exceptions.ServiceError as e:
        print(f"Error creating bucket: {e}")
else:
    print(f"Bucket '{bucket_name}' already exists.")

# Specify the PAR details
par_details = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
    name="par_request_to_the_bucket",
    access_type="AnyObjectWrite",
    time_expires=(datetime.datetime.now() + datetime.timedelta(hours=72)),
    bucket_listing_action="ListObjects"
)

# Create the PAR for the bucket
try:
    preauthenticated_request_response = object_storage_client.create_preauthenticated_request(
        namespace_name=get_namespace_response.data,
        bucket_name=bucket_name,
        create_preauthenticated_request_details=par_details
    )
    par = preauthenticated_request_response.data
    print(f"PAR OCID: {par.id}")
    print(f"PAR Access URI: {par.access_uri}")
except oci.exceptions.ServiceError as e:
    print(f"Error creating PAR: {e}")

# Function to check the image status
def check_image_status(image_id):
    while True:
        try:
            get_image_response = compute_client.get_image(image_id=image_id)
            if get_image_response.data.lifecycle_state == "AVAILABLE":
                print(f"Exporting custom image {image_id} to Object Storage")
                export_image_response = compute_client.export_image(
                    image_id=image_id,
                    export_image_details=oci.core.models.ExportImageViaObjectStorageUriDetails(
                        destination_type="objectStorageUri",
                        destination_uri="https://" + get_namespace_response.data +
                                        ".objectstorage." + config["region"] + ".oci.customer-oci.com" +
                                        par.access_uri + get_image_response.data.display_name + ".img",
                        export_format="OCI"
                    )
                )
                print(export_image_response.data)
                break
            else:
                print(f"Checking resource state for image {image_id}: {get_image_response.data.lifecycle_state}")
                time.sleep(polling_interval)
        except oci.exceptions.ServiceError as e:
            print(f"Error checking resource state for image {image_id}: {e}")
            time.sleep(polling_interval)

# Main execution
if __name__ == "__main__":
    polling_interval = 5  # Set the polling interval to 5 seconds

    # Create a ThreadPoolExecutor for parallel execution
    if image_lst:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(image_lst)) as executor:
            futures = [executor.submit(check_image_status, image_id) for image_id in image_lst]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error during concurrent execution: {e}")

# List objects in the bucket
list_objects_response = object_storage_client.list_objects(
    namespace_name=get_namespace_response.data,
    bucket_name=bucket_name
)
print("Objects in bucket 'image_backup':")
for obj in list_objects_response.data.objects:
    print(obj.name)
