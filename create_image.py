import oci
import json
from pandas.io.json import json_normalize
import pandas as pd
import datetime
import os.path

config = oci.config.from_file()
compute_client = oci.core.ComputeClient(config)

# Create an image source details object
image_source_details = oci.core.models.ImageSourceDetails(
    source_type="objectStorageUri",
    source_uri = "https://sehubjapaciaas.objectstorage.us-ashburn-1.oci.customer-oci.com/p/HcxqBP_FXNcO1hA3AFQFxDLd2srx9dlL8BrEa8NfmfGF9R-pfwDBXMX0pqmIHXW7/n/sehubjapaciaas/b/test_bucket/o/exported-image-python-mysql",
    os_type="linux",
)

# Create an import image request
create_image_request = oci.core.models.CreateImageDetails(
    compartment_id=compartment_id,
    display_name=image_display_name,
    launch_mode="NATIVE",
    image_source_details=image_source_details,
)

# Initiate the import image job
create_image_response = compute_client.create_image(create_image_request)
print(create_image_response.data)
