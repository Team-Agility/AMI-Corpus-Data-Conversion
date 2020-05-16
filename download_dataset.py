import requests
import zipfile
import sys
import os

DATASET_URL = 'https://objectstorage.ap-mumbai-1.oraclecloud.com/n/bm7noglpf2jq/b/FYP-Data/o/dataset.zip'

local_filename = DATASET_URL.split('/')[-1]
with open(local_filename, "wb") as f:
  print("Downloading %s" % local_filename)
  response = requests.get(DATASET_URL, stream=True)
  total_length = response.headers.get('content-length')

  if total_length is None:
    f.write(response.content)
  else:
    dl = 0
    total_length = int(total_length)
    for data in response.iter_content(chunk_size=4096):
      dl += len(data)
      f.write(data)
      done = int(50 * dl / total_length)
      sys.stdout.write("\r[%s%s] %s%s" % ('=' * done, ' ' * (50-done), done * 2, '%'))    
      sys.stdout.flush()


with zipfile.ZipFile(local_filename, 'r') as zip_ref:
  print('\n\nExtracting Dataset. It may take some time ...')
  zip_ref.extractall()

print('Dataset Extracted.')
try:
  os.remove(local_filename)
except OSError:
  pass