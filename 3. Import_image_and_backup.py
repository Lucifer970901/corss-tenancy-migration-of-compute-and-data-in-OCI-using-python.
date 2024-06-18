import oci
import json
import pandas as pd
from pandas import json_normalize
import datetime
import csv
import time
import os.path

#provide the configuration details for the new tenancy.
config = oci.config.from_file(file_location="~/.oci/config_sehubjapaciaasset02")
backup_id_lst = []
backup_name_lst = []
block_storage_client = oci.core.BlockstorageClient(config)
identity = oci.identity.IdentityClient(config)
availability_domains = identity.list_availability_domains(compartment_id=config["compartment_id"])
compute_client = oci.core.ComputeClient(config)

#print(availability_domains.data)

for ad in availability_domains.data:
     availability_domain = ad.name
     break

print(availability_domain)
#create the volume from backup.
with open('Volume_Backup_details.csv', 'r') as file:
    csv_reader = csv.reader(file)
    next(file) #skip the first line/header from listing 
    # Iterate through the rows and fetch volume id and name from each list.
    for row in csv_reader:
        create_volume_response = block_storage_client.create_volume(
        create_volume_details=oci.core.models.CreateVolumeDetails(
        compartment_id=config["compartment_id"],
        availability_domain=availability_domain,
        display_name=row[2],
        volume_backup_id=row[1])
    )
# Get the data from response
print(create_volume_response.data)

# Read the CSV file
df = pd.read_csv("custom_image_PAR_details.csv")
# Loop through each row in the DataFrame and create an image
# Loop through each row in the DataFrame and create an image
for index, row in df.iterrows():
    source_url = row['custom_image_URL']
    image_display_name = row['custom_image_name']
    
    # Create an image source details object using ImageSourceViaObjectStorageUriDetails
    image_source_details = oci.core.models.ImageSourceViaObjectStorageUriDetails(
        source_uri=source_url,
        source_image_type="VMDK"  # Replace with the correct image type, e.g., "qcow2", "vmdk", etc.
    )

    # Create an import image request
    create_image_request = oci.core.models.CreateImageDetails(
        compartment_id=config["compartment_id"],
        display_name=image_display_name,
        launch_mode="NATIVE",
        image_source_details=image_source_details,
    )

    # Initiate the import image job
    create_image_response = compute_client.create_image(create_image_request)
    
    # Print the response for each image
    print(f"Image '{image_display_name}' creation response: {create_image_response.data}")

