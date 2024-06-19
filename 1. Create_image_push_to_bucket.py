import oci
import json
import pandas as pd
from pandas import json_normalize
import datetime
import time
import os.path
import concurrent.futures

# refering to the configuration of old tenancy for the authentication.
config = oci.config.from_file(file_location="~/.oci/config_sehubjapaciaasset01") 
image_lst = []
backup_lst = []
file_lst = []
vnic_lst = []
subnet_lst = []
ip_lst = []
compute_client = oci.core.ComputeClient(config)
object_storage_client = oci.object_storage.ObjectStorageClient(config)
block_storage_client = oci.core.BlockstorageClient(config)
network_client = oci.core.VirtualNetworkClient(config)

#name of the bucket
bucket_name = "image_backup"
#get namespace dynamically
get_namespace_response = object_storage_client.get_namespace(compartment_id=config["compartment_id"])
print(get_namespace_response.data)
################ get the instance details ###################
get_instance_response = compute_client.list_instances(compartment_id=config["compartment_id"])
#print(get_instance_response.data)


################ create the block volume backup  ###################
# List all block volumes in the specified compartment
block_volumes = block_storage_client.list_volumes(compartment_id=config["compartment_id"])

# Loop through the block volumes and print their details
for block_volume in block_volumes.data:
    print("Block Volume Name:", block_volume.display_name)
    print("Block Volume OCID:", block_volume.id)
    # Add more information as needed
    # Create a request to create a block volume backup.
    create_backup_details = oci.core.models.CreateVolumeBackupDetails(
    volume_id=block_volume.id,
    display_name=block_volume.display_name
)
# Make the API call to create the backup.
    try:
        create_backup_response = block_storage_client.create_volume_backup(create_backup_details)
        backup = create_backup_response.data
        print(backup)
        print("Backup OCID:", backup.id)
        print("Backup State:", backup.lifecycle_state)
        backup_lst.append([backup.id,backup.display_name])
    except oci.exceptions.ServiceError as e:
        print("Error creating backup:", e)

# push the backup details to a file
df = pd.DataFrame(backup_lst, columns=["Volume_Backup_ID", "Volume_Backup_Name"])
df = df.dropna()
df.to_csv("Volume_Backup_details.csv")
print(df)    

################ create the custom image  for each instance ###################
################ get the vnic details ###################
list_vnic_attachments_response = compute_client.list_vnic_attachments(compartment_id=config["compartment_id"])
#print(list_vnic_attachments_response.data)
try:
    csv_df = pd.read_csv("list_instances.csv")
    csv_df.dropna()
    i = 0
    print(csv_df)
    for i in csv_df.index:
        compute_id = str(csv_df.iloc[i]["Instance OCID"])
        for a in list_vnic_attachments_response.data:
            if compute_id == a.instance_id:
                vnic_lst.append(a.vnic_id)
                subnet_lst.append(a.subnet_id)
        for b in vnic_lst:
            list_private_ips_response = network_client.list_private_ips(vnic_id = str(b))
            #print(list_private_ips_response.data)
        for c in list_private_ips_response.data:
            ip_lst.append(c.ip_address)
            #ip_lst.append(list_private_ips_response.data.ip_address)
            #print(subnet_lst)

################ get the instance details ###################
        get_instance_response = compute_client.get_instance(compute_id)
#print(get_instance_response.data)


################ create the custom image  for each instance ###################
for instance in get_instance_response.data:
    try:
        create_image_response   = compute_client.create_image(
            create_image_details=oci.core.models.CreateImageDetails(
            compartment_id  = config["compartment_id"],
            instance_id     = instance.id,
            display_name    = instance.display_name,
            launch_mode     = "NATIVE"))
            #append the list with custom image name and ocid
        image_lst.append([create_image_response.data.id])
        print(subnet_lst)
        print(ip_lst)
        #append to the list
        for b in ip_lst:
        for a in subnet_lst:
            file_lst.append([get_instance_response.data.id, get_instance_response.data.display_name, get_instance_response.data.shape, get_instance_response.data.shape_config.ocpus,get_instance_response.data.shape_config.memory_in_gbs, str(b), create_image_response.data.id, str(a),get_instance_response.data.availability_domain, get_instance_response.data.launch_options.boot_volume_type, get_instance_response.data.launch_options.network_type, get_instance_response.data.launch_options.remote_data_volume_type])
    print(file_lst)
    
    except Exception as e:
        print(e)
        pass

print(image_lst)
df = pd.DataFrame(file_lst, columns=["Instance_OCID", "Instance Name", "Shape", "OCPUs", "Memory in GBs", "Private IP", "Custom Image OCID", "subnet OCID","availability domain","boot_volume_type","network_type","remote_data_volume_type"])
df = df.dropna()
df.to_csv("instance_and_VNIC_details.csv")
print(df)

#check if the bucket already exists
def bucket_exists(bucket_name):
    try:
        object_storage_client.get_bucket(namespace_name=get_namespace_response.data, bucket_name=bucket_name)
        return True
    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            return False  # Bucket does not exist
        else:
            raise e  # Other error​

# Create a request to create the bucket if bucket does not exists.
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
        # Make the API call to create the bucket.
        object_storage_client.create_bucket(namespace_name=get_namespace_response.data, create_bucket_details=create_bucket_request)
        print(f"Bucket '{bucket_name}' created successfully.")
    except oci.exceptions.ServiceError as e:
        print(f"Error creating bucket, the bucket might already exists: {e}")
else:
    print(f"Bucket '{bucket_name}' already exists.")

# Specify the PAR details.
par_details = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
    name="par_request_to_the_bucket",  # Replace with a unique name for your PAR for bucket
    access_type="AnyObjectWrite",  # Specify the access type for the bucket
    time_expires=(datetime.datetime.now() + datetime.timedelta(hours=72)),  # Specify the expiration time in hours
    bucket_listing_action="ListObjects"
)

# Create the PAR for the bucket.
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
                print(f"Export the custom image {image_id} to Object Storage")
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
                break  # Exit the loop when the image becomes available
            else:
                print(f"Checking resource state for image {image_id}: {get_image_response.data.lifecycle_state}")
                time.sleep(polling_interval)
        except oci.exceptions.ServiceError as e:
            print(f"Error checking resource state for image {image_id}: {e}")
            time.sleep(polling_interval)


if __name__ == "__main__":
    polling_interval = 5  # Set the polling interval to 5 seconds
    get_namespace_response = object_storage_client.get_namespace(compartment_id=config["compartment_id"])

    # Create a ThreadPoolExecutor with a specified maximum number of workers (threads)
    max_workers = len(image_lst)  # Create one thread per image
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit image check tasks in parallel
        futures = [executor.submit(check_image_status, image_id) for image_id in image_lst]

#list objects
list_objects_response = object_storage_client.list_objects(
    namespace_name=get_namespace_response.data,
    bucket_name="image_backup")

